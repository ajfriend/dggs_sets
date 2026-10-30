'''S2 (aperture 4 quadtree on a cube) via the official s2geometry bindings, with int cell ids.'''
import math

import s2geometry as _s2
from shapely.geometry import Polygon

from . import _adapter
from .core import compaction
from .core.design import design as _design
from .core.tree import Grid, cell_to_parent as _cell_to_parent
from ._adapter import bind


# The hierarchy is pure bit arithmetic on the 64-bit id, which avoids a
# round trip through the SWIG bindings per call. An S2 cell id is
# [3 face bits][2 bits per level][1][zeros], so the lowest set bit
# encodes the level.

def _parent(c):
    lsb = (c & -c) << 2
    return (c & -lsb) | lsb


def _children(c):
    lsb = c & -c
    k = lsb >> 2
    base = c - lsb
    return [base + k, base + 3 * k, base + 5 * k, base + 7 * k]


def _level(c):
    return 30 - ((c & -c).bit_length() - 1) // 2


grid = Grid(parent=_parent, children=_children, resolution=_level)
MAX_RES = 30


def _loop(ring):
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    loop = _s2.S2Loop([_s2.S2LatLng.FromDegrees(p[1], p[0]).ToPoint() for p in ring])
    loop.Normalize()
    return loop


def polygon_to_cells(geo, res):
    '''Cells at `res` whose centers fall inside `geo` (a __geo_interface__).

    S2 has no center-containment fill. Cells in the fixed-level interior
    covering lie entirely inside the polygon, so they're kept as is; only
    the remaining cells of the full covering (every intersecting cell)
    need a center test. Note S2 polygon edges are geodesics.
    '''
    coverer = _s2.S2RegionCoverer()
    coverer.set_fixed_level(res)
    coverer.set_max_cells(2**31 - 1)
    out = set()
    for rings in _adapter.polygons(geo):
        poly = _s2.S2Polygon()
        poly.InitNested([_loop(r) for r in rings])
        interior = {c.id() for c in coverer.GetInteriorCovering(poly)}
        out |= interior
        out.update(
            c.id() for c in coverer.GetCovering(poly)
            if c.id() not in interior and poly.Contains(_s2.S2Cell(c).GetCenter())
        )
    return out


def latlng_to_cell(lat, lng, res):
    return _s2.S2CellId(_s2.S2LatLng.FromDegrees(lat, lng)).parent(res).id()


def cell_to_latlng(cell):
    '''The cell's center, as (lat, lng).'''
    p = _s2.S2CellId(cell).ToLatLng()
    return p.lat().degrees(), p.lng().degrees()


def cell_to_boundary(cell, per_edge=8):
    '''The cell's own polygon, in lng/lat.

    S2 edges are geodesics, so each one is interpolated on the sphere.
    '''
    c = _s2.S2Cell(_s2.S2CellId(cell))
    verts = [c.GetVertex(k) for k in range(4)]
    ring = []
    for a, b in zip(verts, verts[1:] + verts[:1]):
        for i in range(per_edge):
            t = i / per_edge
            x, y, z = ((1 - t) * a.x() + t * b.x(), (1 - t) * a.y() + t * b.y(), (1 - t) * a.z() + t * b.z())
            n = math.sqrt(x * x + y * y + z * z)
            ring.append((math.degrees(math.atan2(y, x)), math.degrees(math.asin(z / n))))
    return Polygon(ring)


compact = bind(compaction.compact, grid)
cocompact = bind(compaction.cocompact, grid)
uncompact = bind(compaction.uncompact, grid)
contains = bind(compaction.contains, grid)
design = bind(_design, grid)
cell_to_parent = bind(_cell_to_parent, grid)
footprint = bind(_adapter.footprint, grid, cell_to_boundary)


def avg_cell_area_km2(res):
    return _adapter.EARTH_AREA_KM2 / (6 * 4**res)
