'''The data the talk uses. See README.md here for sources and licenses.

    states()            -> {name: shapely geometry}      US states
    ct_counties()       -> {name: shapely geometry}      Connecticut's eight counties
    cellsets(m, geoms, r) -> {name: set[int]}            named cellsets: each geometry as cells at r
    nyc_field(name)     -> {cell: minutes | None}        driving minutes from downtown Brooklyn,
                                                         'h3' (res 10) or 's2' (level 16)

The package stores as little as it can. The boundaries are fetched from their
sources on first use and cached under CACHE (override with $DGGS_SETS_CACHE).
Only the NYC fields ship with the package: they can't be regenerated from
public data.
'''
import csv
import gzip
import json
import os
from functools import cache
from importlib.resources import files
from pathlib import Path
from urllib.request import urlretrieve

import s2geometry
from shapely.geometry import shape

_DIR = files(__name__)
CACHE = Path(os.environ.get('DGGS_SETS_CACHE', Path.home() / '.cache' / 'dggs_sets'))

# US Census cartographic boundaries (2010, 1:500k) as GeoJSON, pinned to the copy in h3coco
STATES_URL = 'https://raw.githubusercontent.com/ajfriend/h3coco/931c1f0f17f8/src/h3coco/data/us_states.json'
# CT DEEP's "Connecticut County Index" feature service, as GeoJSON in lng/lat
COUNTIES_URL = ('https://services1.arcgis.com/FjPcSmEFuDYlIdKC/arcgis/rest/services/'
                'Connecticut_County_Index/FeatureServer/0/query?where=1%3D1&outFields=COUNTY&outSR=4326&f=geojson')


def fetch(name, url):
    '''The cached file `name`, downloaded from `url` on first use.'''
    path = CACHE / name
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        print(f'dggs_sets.data: fetching {url} -> {path}')
        urlretrieve(url, path)
    return path


def _geojson(path, key):
    gj = json.loads(path.read_text(encoding='utf-8'))
    return {f['properties'][key]: shape(f['geometry']).buffer(0) for f in gj['features']}


@cache
def states():
    '''US state boundaries: {name: shapely geometry}.'''
    return _geojson(fetch('us_states.json', STATES_URL), 'NAME')


@cache
def ct_counties():
    '''Connecticut's eight counties: {name: shapely geometry}.'''
    return _geojson(fetch('ct_counties.geojson', COUNTIES_URL), 'COUNTY')


def cellsets(m, geoms, res):
    '''Named cellsets, {name: cells at `res`}, for a system module `m` (dggs_sets.h3, .s2 or .a5).'''
    return {name: m.polygon_to_cells(geom, res) for name, geom in geoms.items()}


_FIELDS = {
    'h3': ('nyc_h3r10_field.csv.gz', lambda cell: int(cell, 16)),
    's2': ('nyc_s2l16_field.csv.gz', lambda token: s2geometry.S2CellId.FromToken(token).id()),
}


@cache
def nyc_field(name):
    '''Driving minutes from downtown Brooklyn to every cell in the five-borough box,
    None where unreachable: {cell: minutes}. `name` is 'h3' (res 10) or 's2' (level 16).'''
    filename, parse = _FIELDS[name]
    with gzip.open(_DIR / filename, 'rt') as f:
        return {parse(r['cell']): float(r['minutes']) if r['minutes'] else None for r in csv.DictReader(f)}
