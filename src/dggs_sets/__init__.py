'''Compaction, co-compaction and set design across DGGSs: H3, S2 and A5.

The package has four parts:

    h3, s2, a5   the three systems behind one interface (below); start here
    core         the algorithms, written to read like pseudocode: tree, compaction, design
    data         the talk's data: US states, Connecticut's counties, the NYC drive-time fields
    plot         drawing helpers for cells, footprints and bags

Each system module exposes the same interface:

    polygon_to_cells(geo, res) -> set[int]
    compact(cells) -> set[int]
    cocompact(cells) -> set[int]
    uncompact(bag, res) -> set[int]
    contains(bag, cell) -> bool
    latlng_to_cell(lat, lng, res) -> int
    cell_to_latlng(cell) -> (lat, lng)          # the cell's center
    cell_to_parent(cell, res) -> int            # by ID; the cell itself at its own res
    design(weights, lam, size) -> set[int]      # max sum(w) - lam*size; size: cells/compact/cocompact
    cell_to_boundary(cell) -> shapely Polygon   # the geometric cell, G(c)
    footprint(cell, res) -> shapely geometry    # union of descendants' polygons, F_r(c)
    avg_cell_area_km2(res) -> float
    MAX_RES: int

The system modules bind the core algorithms to their grid.
'''
from . import a5, h3, s2

SYSTEMS = {'h3': h3, 's2': s2, 'a5': a5}

__all__ = ['SYSTEMS', 'a5', 'h3', 's2']
