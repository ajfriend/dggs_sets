'''A5 (pentagonal, aperture 4) via pya5, with int cell ids.'''
import a5 as _a5
from shapely.geometry import Polygon

from . import _adapter
from .core import compaction, tree as _tree
from .core.design import design as _design
from ._adapter import bind, bind_tree
from .core.tree import Grid

grid = Grid(
    parent=_a5.cell_to_parent,
    children=_a5.cell_to_children,
    resolution=_a5.get_resolution,
)
MAX_RES = _a5.MAX_RESOLUTION


def polygon_to_cells(geo, res):
    '''Cells at `res` whose centers fall inside `geo` (a __geo_interface__).

    A5's native fill takes one polygon at a time and returns a compacted
    result with a trailing marker, so fill each part and uncompact.
    '''
    out = set()
    for rings in _adapter.polygons(geo):
        rings = [[tuple(p[:2]) for p in ring] for ring in rings]
        packed = _a5.polygon_to_cells(rings, res, {'containment': 'center'})
        out.update(c for c in _a5.uncompact(packed) if not _a5.is_compaction_marker(c))
    return out


def latlng_to_cell(lat, lng, res):
    return _a5.lonlat_to_cell((lng, lat), res)


def cell_to_latlng(cell):
    '''The cell's center, as (lat, lng).'''
    lng, lat = _a5.cell_to_lonlat(cell)
    return lat, lng


def cell_to_boundary(cell):
    '''The cell's own polygon, in lng/lat.'''
    return Polygon(_a5.cell_to_boundary(cell))


compact = bind_tree(compaction.compact, grid)
cocompact = bind_tree(compaction.cocompact, grid)
uncompact = bind(compaction.uncompact, grid)
contains = bind(compaction.contains, grid)
design = bind_tree(_design, grid)
cell_to_parent = bind(_tree.cell_to_parent, grid)
footprint = bind(_adapter.footprint, grid, cell_to_boundary)


def avg_cell_area_km2(res):
    return _adapter.EARTH_AREA_KM2 / _a5.get_num_cells(res)
