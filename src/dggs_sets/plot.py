'''Drawing helpers shared by the figure scripts.

Cells and bags are drawn in lng/lat, filled as in (green) or carved out
(hatched), with each token outlined by its footprint.
'''
from collections import Counter
from functools import cache
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import shapely
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath
from PIL import Image
from shapely.ops import polylabel

from dggs_sets.core.tree import cell_to_parent, descendants

IN = dict(fc='#66c2a5', ec='none')
CARVED = dict(fc='white', ec='#9a9a9a', hatch='////', lw=0)
NEW, OLD = '#222', '#bbb'
TOKEN = dict(lw=1.4, solid_joinstyle='round')
BOUNDARY = dict(color='#c0392b', lw=1.5, ls=(0, (2, 2)))
WIDTH = 12   # inches; height follows the map's aspect


def save(fig, path, dpi=100, colors=64, palette=None, **kw):
    '''Write the figure as a palette PNG. The figures are flat colors, so 64
    colors look the same as RGBA and take 4-6x less space; the lambda movie,
    with a basemap and a colormap, gets 256. The frames of a sequence all pass
    the same `palette` (from `shared_palette`), so nothing shifts between
    them; `colors` only matters without one.'''
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, facecolor='white', **kw)
    img = Image.open(path).convert('RGB')
    if palette is None:
        quantized = img.quantize(colors, dither=Image.Dither.NONE)   # no dither: its noise compresses badly
    else:   # Pillow's palette mapping is approximate, but it's the same for every frame
        quantized = img.quantize(palette=palette, dither=Image.Dither.NONE)
    quantized.save(path, optimize=True)


def shared_palette(fig, dpi=100, colors=256):
    '''The palette image for a sequence of frames, from the one frame that has
    every color in it; pass it to `save` for each frame.'''
    buf = BytesIO()
    fig.savefig(buf, dpi=dpi, facecolor='white', format='png')
    return Image.open(buf).convert('RGB').quantize(colors, dither=Image.Dither.NONE)


def patch(geom, **kw):
    '''A matplotlib patch for a shapely (Multi)Polygon, holes included.'''
    paths = []
    for p in shapely.get_parts(geom):
        for ring in [p.exterior, *p.interiors]:
            paths.append(MPath(np.array(ring.coords), closed=True))
    return PathPatch(MPath.make_compound_path(*paths), **kw)


def outline(ax, geom, **kw):
    '''Draw every ring of a (Multi)Polygon, holes included.'''
    for p in shapely.get_parts(geom):
        for ring in [p.exterior, *p.interiors]:
            ax.plot(*ring.xy, **kw)


def inside_point(geom, tolerance=1e-4):
    '''A point well inside a (Multi)Polygon, for a label or a marker: the pole
    of inaccessibility of its largest part.'''
    return polylabel(max(shapely.get_parts(geom), key=lambda p: p.area), tolerance=tolerance)


def depths(grid, bag, r):
    '''Fine cell -> number of tokens covering it.'''
    return Counter(c for t in bag for c in descendants(grid, t, r))


def nesting(grid, bag):
    '''Token -> 1 + the number of its ancestors that are also tokens.'''
    return {t: 1 + sum(cell_to_parent(grid, t, k) in bag for k in range(grid.resolution(t)))
            for t in bag}


# every step of a sequence redraws the same cells and footprints
@cache
def cell_polygon(m, c):
    return m.cell_to_boundary(c)


@cache
def footprint(m, t, r):
    return m.footprint(t, r)


def region(m, cells):
    return shapely.union_all([cell_polygon(m, c) for c in sorted(cells)])   # sorted: same figure every run


def frame(geoms, pad=0.03, width=WIDTH):
    '''Axes limits, aspect and figure size that fit `geoms` (lng/lat), with
    `pad` as a fraction of the longer side.'''
    x0, y0, x1, y1 = shapely.union_all(geoms).bounds
    pad = pad * max(x1 - x0, y1 - y0)
    aspect = 1 / np.cos(np.deg2rad((y0 + y1) / 2))
    height = width * (y1 - y0 + 2 * pad) * aspect / (x1 - x0 + 2 * pad)
    return (x0 - pad, x1 + pad), (y0 - pad, y1 + pad), aspect, (width, height)


def draw_tokens(ax, m, tokens, r, color=lambda t: NEW, fill=IN, **kw):
    '''Fill each fine cell in or carved out, and outline each token's footprint.'''
    depth = depths(m.grid, tokens, r)
    ax.add_patch(patch(region(m, [c for c, n in depth.items() if n % 2]), **fill))
    carved = [c for c, n in depth.items() if n % 2 == 0]
    if carved:
        ax.add_patch(patch(region(m, carved), **CARVED))
    for t in sorted(tokens, key=lambda t: (color(t) == NEW, m.grid.resolution(t), t)):   # new on top
        outline(ax, footprint(m, t, r), color=color(t), **(TOKEN | kw))


def draw_bag(path, m, tokens, r, view, is_new=lambda t: True, boundary=None, hole=None):
    '''Write one figure: cells in or carved out, and each token's footprint.
    `boundary` is drawn as the region's true edge; `hole` (a geometry, say a
    missing cell) is hatched like a carved-out cell.'''
    xlim, ylim, aspect, size = view
    fig = plt.figure(figsize=size)
    ax = fig.add_axes((0, 0, 1, 1))
    draw_tokens(ax, m, tokens, r, color=lambda t: NEW if is_new(t) else OLD)
    if boundary is not None:
        outline(ax, boundary, **BOUNDARY)
    if hole is not None:
        ax.add_patch(patch(hole, **CARVED | dict(ec=NEW, lw=TOKEN['lw'])))   # hatched, with the boundary drawn
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect(aspect)
    ax.set_axis_off()
    save(fig, path, dpi=200)
    plt.close(fig)
    print(f'  wrote {path}')
