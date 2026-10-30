'''Connecticut's counties as cell sets, in three steps, for each DGGS.

Same style as the CT slides from the H3 talk. Each county is filled at one
resolution r, compacted, and drawn as:

1. geo: the compacted cells, each as its geometric cell G(c), the cell's own
   polygon (`cell_to_boundary`). In H3 and A5, children don't nest exactly
   inside their parent, so coarse cells next to finer ones gap and overlap.
2. footprint: the compacted cells, each as its footprint F_r(c), the area
   covered by its descendants at r (for H3, the Gosper island). These tile
   exactly.
3. fine: the filled cells at r, each as its own polygon. They cover the
   same area as the footprints in step 2.

S2 children nest exactly, so G(c) = F_r(c) and it skips step 2.

Before those, `coarse` draws the whole state in each system at a coarse
resolution (COARSE: a few thousand cells) and one level coarser, to show each
system's cell shapes.

    uv run scripts/plot_ct.py
'''
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import shapely
from matplotlib.collections import PolyCollection

from dggs_sets import SYSTEMS, data
from dggs_sets.plot import BOUNDARY, IN, frame, inside_point, outline, patch, save

RES = {'h3': 8, 's2': 14, 'a5': 13}
COARSE = {'h3': 7, 's2': 12, 'a5': 11}   # the whole state in a few thousand cells of similar area
STATE = BOUNDARY | dict(lw=0.8, ls=(0, (1, 1.5)))   # the state line: the same red, as a fine dotted line
OUT = Path(__file__).parent.parent / 'talk' / 'figs'

QUERY_POINT = (41.76, -72.67)   # the query slide's example: downtown Hartford
NUDGE = {   # county name -> (dlng, dlat), tuned by eye
    'Fairfield': (0.02, 0.05),
    'Middlesex': (0.02, -0.015),
    'New London': (0.03, 0),
}
CMAP = 'Dark2'
XLIM = (-73.78, -71.74)
YLIM = (40.95, 42.1)
FIGSIZE = (20, 20)


# outlines: each returns a list of (N, 2) arrays of (lng, lat)

def geo(m, cell, res):
    return _exteriors(m.cell_to_boundary(cell))


def footprint(m, cell, res):
    return _exteriors(m.footprint(cell, res))


def _exteriors(geom):
    return [np.array(p.exterior.coords) for p in shapely.get_parts(geom)]


# view: (which cell set to draw, how to draw each cell, edge width)
# fine cells are tiny at r, so their edges are drawn thinner
VIEWS = {
    'fine': ('fine', geo, 0.1),
    'geo': ('compact', geo, 1),
    'footprint': ('compact', footprint, 1),
}
STEPS = {
    'h3': ['geo', 'footprint', 'fine'],
    's2': ['geo', 'fine'],
    'a5': ['geo', 'footprint', 'fine'],
}


def new_axes():
    fig, ax = plt.subplots(figsize=FIGSIZE)
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    # plain lng/lat axes, scaled so the map isn't squashed
    ax.set_aspect(1 / np.cos(np.deg2rad(np.mean(YLIM))))
    ax.set_axis_off()
    return fig, ax


def draw(m, covered, outline, res, ax, **kw):
    cmap = plt.get_cmap(CMAP)
    polys, facecolors = [], []
    for i, cells in enumerate(covered):
        for cell in cells:
            for ring in outline(m, cell, res):
                polys.append(ring)
                facecolors.append(cmap(i % cmap.N))
    ax.add_collection(PolyCollection(polys, facecolors=facecolors, **kw))


def label(ax, counties):
    '''Each county's name at its centroid, or at the point deepest inside it
    when the centroid falls outside (a concave county), plus any NUDGE.'''
    for name, geom in counties.items():
        p = geom.centroid if geom.contains(geom.centroid) else inside_point(geom)
        dx, dy = NUDGE.get(name, (0, 0))
        p = shapely.Point(p.x + dx, p.y + dy)
        ax.text(p.x, p.y, name, ha='center', va='center', fontsize=28, fontweight='bold', color='#222',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='none', alpha=0.8))


def coarse():
    '''The state as coarse cells, at COARSE and one level coarser, one figure
    per system and level: ct_state_{name}_{res}.png.'''
    geom = data.states()['Connecticut']
    xlim, ylim, aspect, figsize = frame([geom], pad=0.08)
    for name, m in SYSTEMS.items():
        for res, lw in [(COARSE[name], 0.6), (COARSE[name] - 1, 1.0)]:   # coarser cells, heavier edges
            cells = m.polygon_to_cells(geom, res)
            fig, ax = plt.subplots(figsize=figsize)
            ax.add_collection(PolyCollection([geo(m, c, res)[0] for c in sorted(cells)],
                                             facecolors=IN['fc'], edgecolors='black', linewidths=lw))
            outline(ax, geom, **STATE)
            ax.set_xlim(*xlim)
            ax.set_ylim(*ylim)
            ax.set_aspect(aspect)
            ax.set_axis_off()
            path = OUT / f'ct_state_{name}_{res}.png'
            save(fig, path, dpi=300, bbox_inches='tight')
            plt.close(fig)
            print(f'{name} res {res}: {len(cells)} cells, wrote {path}')


def counties_h3_7(ax, lw=0.3):
    '''Draw the counties as H3 res-7 cells on `ax`; the base of the two figures below.'''
    m, res = SYSTEMS['h3'], 7
    counties = data.ct_counties()
    draw(m, [sorted(cells) for cells in data.cellsets(m, counties, res).values()], geo, res, ax,
         alpha=0.5, edgecolor='black', linewidth=lw)
    return counties


def named():
    '''The counties with their names, for the "collections of cellsets" slide.'''
    fig, ax = new_axes()
    counties = counties_h3_7(ax)
    label(ax, counties)
    path = OUT / 'ct_counties_h3_7.png'
    save(fig, path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'wrote {path}')


def query():
    '''A zoom on the query slide's point and its res-7 cell, over the counties.'''
    lat, lng = QUERY_POINT
    cell = SYSTEMS['h3'].latlng_to_cell(lat, lng, 7)
    fig, ax = plt.subplots(figsize=(9, 5.4))
    counties_h3_7(ax, lw=0.6)
    ax.add_patch(patch(SYSTEMS['h3'].cell_to_boundary(cell), fc='none', ec='black', lw=3.5))
    ax.plot(lng, lat, 'o', ms=12, mfc=BOUNDARY['color'], mec='white', mew=2)
    ax.set_xlim(lng - 0.36, lng + 0.36)   # Hartford county and its neighbors, wide so it fits under the bullets
    ax.set_ylim(lat - 0.16, lat + 0.16)
    ax.set_aspect(1 / np.cos(np.deg2rad(lat)))
    ax.set_axis_off()
    path = OUT / 'ct_query_h3_7.png'
    save(fig, path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'wrote {path}; the point is in cell {cell:x}')


def gap():
    '''The compacted counties (H3 res 8, geometric cells) with a point marked in
    a gap: inside the counties' cells, outside every compacted cell's polygon.
    The gap is the biggest one beside Hartford's coarsest cell, for the
    "what's going on with those gaps?" slide.'''
    m, res = SYSTEMS['h3'], 8
    cellsets = data.cellsets(m, data.ct_counties(), res)
    compacted = {name: sorted(m.compact(cells)) for name, cells in cellsets.items()}
    covered = shapely.union_all([m.cell_to_boundary(c) for cells in cellsets.values() for c in cells])
    drawn = shapely.union_all([m.cell_to_boundary(c) for cells in compacted.values() for c in cells])
    gaps = shapely.get_parts(shapely.set_precision(covered.difference(drawn), 1e-9))
    biggest = m.cell_to_boundary(min(compacted['Hartford'], key=m.grid.resolution))
    beside = [g for g in gaps if g.distance(biggest) < 1e-6]
    big = [g for g in beside if g.area > 0.2 * max(g.area for g in beside)]
    # the gap at the hexagon's upper-right vertex
    upper_right = max((v for v in biggest.exterior.coords if v[1] > biggest.centroid.y), key=lambda v: v[0])
    p = inside_point(min(big, key=lambda g: g.distance(shapely.Point(upper_right))))
    fig, ax = new_axes()
    draw(m, compacted.values(), geo, res, ax, alpha=0.5, edgecolor='black', linewidth=1)
    ax.plot(p.x, p.y, 'x', ms=22, mec='#1f3a93', mew=4)   # a blue X against the orange: visible, and the gap shows through
    path = OUT / f'ct_gap_h3_{res}.png'
    save(fig, path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'wrote {path}; the gap point is ({p.y:.4f}, {p.x:.4f})')


def main():
    coarse()
    named()
    query()
    gap()
    counties = data.ct_counties()
    for name, m in SYSTEMS.items():
        res = RES[name]
        fine = data.cellsets(m, counties, res).values()
        sets = {
            'fine': [sorted(cells) for cells in fine],
            'compact': [sorted(m.compact(cells)) for cells in fine],
        }
        print(f'{name} res {res}: ' + ', '.join(
            f'{sum(map(len, covered)):,} {kind} cells' for kind, covered in sets.items()))
        for tag in STEPS[name]:
            kind, outline, lw = VIEWS[tag]
            fig, ax = new_axes()
            draw(m, sets[kind], outline, res, ax, alpha=0.5, edgecolor='black', linewidth=lw)
            path = OUT / f'ct_{name}_{tag}_{res}.png'
            save(fig, path, dpi=200, bbox_inches='tight')
            plt.close(fig)
            print(f'  wrote {path}')


if __name__ == '__main__':
    main()
