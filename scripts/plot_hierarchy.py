'''One cell, then its children, grandchildren and great-grandchildren, for the
hierarchy slides.

H3 and A5 get one figure per level. The parent is the cell at the point
plot_query.py draws (imported from there, so the H3 figures stay the same
cell); the descendants are its 7, 49 and 343 cells (H3) or 4, 16 and 64 (A5)
at the next three resolutions. They don't tile the parent exactly: their
union is a different region, which the footprint slides come back to. The
descendant figures dash the parent's outline so the difference shows.

S2 children tile their parent exactly, so one figure does all three levels:
the cell's 4 children, one of them split into 4, one of those split again.

    uv run scripts/plot_hierarchy.py
'''
from pathlib import Path

import matplotlib.pyplot as plt

from dggs_sets import a5, h3, s2
from dggs_sets.plot import IN, frame, outline, patch, save
from plot_query import CELL_RES, LAT, LNG

OUT = Path(__file__).parent.parent / 'talk' / 'figs'
LEVELS = [('cell', 0, 2), ('children', 1, 2), ('grandchildren', 2, 1.2), ('greatgrandchildren', 3, 0.7)]   # (tag, levels down, edge width)
CASES = [('h3', h3, CELL_RES), ('a5', a5, 8)]   # A5 res 8 is about 500 km2, the nearest to H3 res 5's 250
S2_LEVEL = 9                                    # about 320 km2


def levels(name, m, res):
    '''The cell at (LAT, LNG) and its descendants, one figure per level.'''
    parent = m.latlng_to_cell(LAT, LNG, res)
    g = m.cell_to_boundary(parent)
    polys = {down: [m.cell_to_boundary(c) for c in sorted(m.uncompact({parent}, res + down))]
             for _, down, _ in LEVELS}
    xlim, ylim, aspect, figsize = frame([p for ps in polys.values() for p in ps], pad=0.08, width=8)   # one frame, so they flip cleanly
    for tag, down, lw in LEVELS:
        fig, ax = plt.subplots(figsize=figsize)
        for p in polys[down]:
            ax.add_patch(patch(p, fc=IN['fc'], ec='black', lw=lw))
        if down:
            outline(ax, g, color='black', lw=2, ls='--')
        finish(fig, ax, (xlim, ylim, aspect), OUT / f'hierarchy_{name}_{tag}.png', f'{len(polys[down])} cells')


def nested_s2():
    '''One S2 cell with its children, one child's children and one grandchild's
    children, all in one figure: they nest exactly.'''
    parent = s2.latlng_to_cell(LAT, LNG, S2_LEVEL)
    xlim, ylim, aspect, figsize = frame([s2.cell_to_boundary(parent)], pad=0.08, width=8)
    fig, ax = plt.subplots(figsize=figsize)
    cell = parent
    for down, lw in [(1, 2), (2, 1.4), (3, 0.9)]:
        kids = sorted(s2.uncompact({cell}, S2_LEVEL + down))
        for k in kids:
            ax.add_patch(patch(s2.cell_to_boundary(k), fc=IN['fc'], ec='black', lw=lw))
        cell = kids[0]   # split the same corner each time
    finish(fig, ax, (xlim, ylim, aspect), OUT / 'hierarchy_s2_nested.png', 'children, grandchildren, great-grandchildren')


def finish(fig, ax, view, path, what):
    xlim, ylim, aspect = view
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect(aspect)
    ax.set_axis_off()
    save(fig, path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f'wrote {path}: {what}')


def main():
    for name, m, res in CASES:
        levels(name, m, res)
    nested_s2()


if __name__ == '__main__':
    main()
