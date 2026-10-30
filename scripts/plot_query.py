'''One H3 cell, drawn as its geometric cell over its footprint, for the
membership-query slides.

The two marked points are where the geometric query goes wrong: one lies in
the hexagon but not the footprint (a false hit), the other in the footprint
but not the hexagon (a miss). plot_hierarchy.py draws the same cell.

    uv run scripts/plot_query.py
'''
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from dggs_sets import h3
from dggs_sets.plot import BOUNDARY, frame, inside_point, patch, save

LAT, LNG, CELL_RES = 41.6, -72.7, 5   # the cell: res 5, in the middle of Connecticut
R = 9                                 # the footprint's resolution
OUT = Path(__file__).parent.parent / 'talk' / 'figs'

FILL = plt.get_cmap('Dark2')(0)


def main():
    cell = h3.latlng_to_cell(LAT, LNG, CELL_RES)
    g = h3.cell_to_boundary(cell)
    f = h3.footprint(cell, R)

    xlim, ylim, aspect, figsize = frame([g, f], pad=0.08, width=8)
    fig, ax = plt.subplots(figsize=figsize)
    ax.add_patch(patch(f, fc=FILL, alpha=0.5, ec='none'))
    ax.add_patch(patch(g, fill=False, ec='black', lw=2, ls='--'))
    for region, text in [(g.difference(f), 'in the hexagon,\nnot the footprint'),
                         (f.difference(g), 'in the footprint,\nnot the hexagon')]:
        p = inside_point(region, tolerance=1e-6)
        ax.plot(p.x, p.y, 'o', color=BOUNDARY['color'], ms=12)
        # push the label outward, away from the cell's center
        dx, dy = p.x - g.centroid.x, p.y - g.centroid.y
        out = 40 * np.array([dx, dy]) / np.hypot(dx, dy)
        ax.annotate(text, (p.x, p.y), xytext=out, textcoords='offset points', fontsize=15, color='#333',
                    ha='left' if dx > 0 else 'right', va='center',
                    arrowprops=dict(arrowstyle='-', color='#999', lw=1, shrinkA=2, shrinkB=7))

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect(aspect)
    ax.set_axis_off()
    path = OUT / 'query_geometric_vs_footprint.png'
    save(fig, path, dpi=200, bbox_inches='tight')
    print(f'wrote {path}')


if __name__ == '__main__':
    main()
