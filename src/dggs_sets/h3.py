'''H3 (aperture 7 hexagons) via h3-py, with int cell ids.'''
from h3.api import basic_int as _h3
from shapely.geometry import Polygon

from . import _adapter
from .core import compaction
from .core.design import design as _design
from .core.tree import Grid, cell_to_parent as _cell_to_parent
from ._adapter import bind

grid = Grid(
    parent=_h3.cell_to_parent,
    children=_h3.cell_to_children,
    resolution=_h3.get_resolution,
)
MAX_RES = 15


def polygon_to_cells(geo, res):
    '''Cells at `res` whose centers fall inside `geo` (a __geo_interface__).'''
    geo = getattr(geo, '__geo_interface__', geo)
    return set(_h3.geo_to_cells(geo, res))


def latlng_to_cell(lat, lng, res):
    return _h3.latlng_to_cell(lat, lng, res)


def cell_to_latlng(cell):
    '''The cell's center, as (lat, lng).'''
    return _h3.cell_to_latlng(cell)


def cell_to_boundary(cell):
    '''The cell's own polygon, in lng/lat.'''
    return Polygon([(lng, lat) for lat, lng in _h3.cell_to_boundary(cell)])


compact = bind(compaction.compact, grid)
cocompact = bind(compaction.cocompact, grid)
uncompact = bind(compaction.uncompact, grid)
contains = bind(compaction.contains, grid)
design = bind(_design, grid)
cell_to_parent = bind(_cell_to_parent, grid)
footprint = bind(_adapter.footprint, grid, cell_to_boundary)


def avg_cell_area_km2(res):
    return _adapter.EARTH_AREA_KM2 / _h3.get_num_cells(res)
