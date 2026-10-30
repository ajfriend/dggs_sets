'''Compaction-aware set design on a NYC isochrone, for Part 2, in H3 and S2.

The field: driving minutes from downtown Brooklyn to every cell in the five
boroughs (None = unreachable), in H3 res 10
and in S2 level 16, the S2 level closest in cell area. Choose a zone S
maximizing

    sum(w[c] for c in S) - lam * size(S),     w[c] = T - minutes[c]

so a cell under T = 20 minutes earns its slack, a cell past T costs its
overshoot, and an unreachable cell (water, parks) is free. The isochrone
I_T is the lam = 0 answer, the most fidelity any zone can have; every
other zone keeps a share of it, reported as "% fidelity":

    fidelity(I_T) - fidelity(S) = sum over dropped cells of (T - m) + sum over bought cells of (m - T)

For each system (prefix `design` for H3, `design_s2` for S2):

- {prefix}_field.png (the field alone), {prefix}_exact.png (the isochrone,
  labeled like the field), {prefix}_iso.png (the same, labeled like the movie), then
  {prefix}_{k}.png for the k-th penalty in LAMS (the "movie"): each cell
  colored by minutes - T (blue inside, white at T, red past
  it) over a basemap, the compacted cells outlined in black, the zone's edge
  in neon green. The co-compacted sizes are only printed; their pictures show
  nothing new.
- {prefix}_frontier.png: % fidelity vs description
  size, sweeping lam, for size = cells, compacted cells and co-compacted
  tokens; dashed, the compaction-aware zones co-compacted afterwards.

The universe is UNIVERSE, a box around the isochrone cut from the
five-borough field: every cell in it is either reached (a drive time) or
verified unreachable (free). Cells outside it are unknown, so they are
absent from `weights` and never chosen; the maps draw the whole universe,
so its rectangle shows.

    uv run scripts/plot_design.py
'''
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

import contextily as ctx
import matplotlib.pyplot as plt
import numpy as np
import shapely
from matplotlib.collections import PolyCollection
from matplotlib.colors import BoundaryNorm, ListedColormap

from dggs_sets.plot import cell_polygon, footprint, frame, outline, region, save, shared_palette
from dggs_sets import SYSTEMS, data

OUT = Path(__file__).parent.parent / 'talk' / 'figs'
T = 20.0
LAMS = [0.001, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0,
        50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0]   # the movie's frames; the last ones go very coarse
SWEEP = np.geomspace(1e-3, 30, 40)               # the frontier
SIZES = {'cells': 'cells', 'compact': 'compacted', 'cocompact': 'co-compacted'}
COLORS = {'cells': '#8c8c8c', 'compact': '#7570b3', 'cocompact': '#1b9e77'}
# the universe: the cells we know about, a box around the isochrone (lng/lat min, max)
UNIVERSE = (-74.15, 40.56, -73.74, 40.84)
ORIGIN = (40.6928, -73.9866)                     # downtown Brooklyn
# cells by minutes - T, on a stepped RdBu ramp, 2 minutes per step: blue
# inside, red past T. Stepped, the colorbar is 20 flat bands and the cells use few colors, which
# the movie's shared palette (see `movie`) then keeps identical from frame to frame.
STEPS = np.linspace(-T, T, 21)
RAMP = ListedColormap(plt.get_cmap('RdBu_r')(np.linspace(0, 1, len(STEPS) - 1)))
NORM = BoundaryNorm(STEPS, RAMP.N)
FIELD_LABEL = f'minutes − {T:g}'
UNREACHABLE = '#c3c2b7'
NEON = '#39ff14'
TILES = ctx.providers.Esri.WorldGrayCanvas   # light grey, no API key; credit on the figure
ZOOM = 13


@dataclass(frozen=True)
class Case:
    '''One DGGS's version of the example.'''
    name: str                      # 'h3' or 's2': the system, and the field in dggs_sets.data
    r: int                         # the field's resolution
    prefix: str                    # the figures' file prefix

    @property
    def m(self):
        return SYSTEMS[self.name]   # the dggs_sets module


CASES = [Case('h3', 10, 'design'), Case('s2', 16, 'design_s2')]


def load_field(case):
    '''Cell -> driving minutes, or None if unreachable, for every cell in the universe.'''
    x0, y0, x1, y1 = UNIVERSE

    def inside(cell):
        lat, lng = case.m.cell_to_latlng(cell)
        return y0 <= lat <= y1 and x0 <= lng <= x1

    return {c: t for c, t in data.nyc_field(case.name).items() if inside(c)}


def kept(case, desc, weights, iso):
    '''The fidelity of the zone `desc` describes, as a percentage of the
    isochrone's. The isochrone holds every cell with positive weight, so it
    is the lam = 0 answer and no zone has more.'''
    zone = case.m.uncompact(desc, case.r)
    return 100 * sum(weights[c] for c in zone) / sum(weights[c] for c in iso)


def sweep(case, weights, iso):
    '''Per size: (description size, % fidelity) at each lam. 'post' is the
    compaction-aware zone co-compacted afterwards: the same fidelity as
    'compact', at co-compaction's size, but chosen without knowing about it.'''
    m = case.m
    curves = {size: [] for size in [*SIZES, 'post']}
    for lam in SWEEP:
        descs = {size: m.design(weights, lam, size) for size in SIZES}
        for size, d in descs.items():
            curves[size].append((len(d), kept(case, d, weights, iso)))
        post = m.cocompact(m.uncompact(descs['compact'], case.r))
        curves['post'].append((len(post), curves['compact'][-1][1]))
    return curves


def basemap(xlim, ylim, zoom=ZOOM):
    '''The view's basemap tiles, fetched once and warped to lng/lat.'''
    img, ext = ctx.bounds2img(xlim[0], ylim[0], xlim[1], ylim[1], zoom=zoom, source=TILES, ll=True)
    return ctx.warp_tiles(img, ext, 'EPSG:4326')


def field_layer(case, minutes):
    '''Every cell in the universe: reached cells by minutes - T, unreachable in grey.
    Cells outside it are unknown, so the map shows the universe's edge.'''
    cells = sorted(minutes)
    polys = [np.array(cell_polygon(case.m, c).exterior.coords) for c in cells]
    colors = [UNREACHABLE if minutes[c] is None else RAMP(NORM(minutes[c] - T)) for c in cells]
    return polys, colors


def movie(case, view, tiles, weights, minutes, iso, exact):
    '''One figure per frame: minutes - T for every
    cell over a basemap, the compacted cells in black, the zone's edge in green.
    {prefix}_field.png is the field alone, {prefix}_exact.png the
    isochrone labeled like the field (the slides introduce them as one map),
    {prefix}_iso.png the isochrone labeled like the movie (its lead-in), then
    one per penalty.'''
    m, r = case.m, case.r
    frames = [('field', None), ('exact', exact), ('iso', exact)]
    frames += [(k, {size: m.design(weights, lam, size) for size in ('compact', 'cocompact')})
               for k, lam in enumerate(LAMS)]
    polys, colors = field_layer(case, minutes)
    # the field and the exact isochrone show the whole universe, with the scale; the movie
    # zooms to its largest zone (the first penalty's) and drops the scale, introduced by then
    widest = region(m, m.uncompact(frames[3][1]['compact'], r))
    zoomed = frame([widest], pad=0.04)
    zoomed_tiles = basemap(*zoomed[:2], zoom=ZOOM + 1)

    def draw(tag, descs):
        '''The frame as a figure, with its zone and % fidelity (None for the field).'''
        overview = descs is None or tag == 'exact'
        xlim, ylim, aspect, figsize = view if overview else zoomed
        img, extent = tiles if overview else zoomed_tiles
        fig = plt.figure(figsize=figsize)
        ax = fig.add_axes((0, 0, 1, 1))
        ax.imshow(img, extent=extent, interpolation='bilinear', zorder=0)
        ax.add_collection(PolyCollection(polys, facecolors=colors, edgecolors='face', lw=0.2, alpha=0.75))
        zone = err = None
        if descs is not None:
            zone, err = descs['compact'], kept(case, descs['compact'], weights, iso)
            for t in sorted(zone, key=lambda t: (m.grid.resolution(t), t)):
                outline(ax, footprint(m, t, r), color='#111', lw=0.5, solid_joinstyle='round')
            outline(ax, region(m, m.uncompact(zone, r)), color=NEON, lw=2.5, solid_joinstyle='round')
        # the field and the exact isochrone share a label: the slides introduce them as one map
        label = FIELD_LABEL if overview else f'{len(zone):,} cells · {err:.1f}% fidelity'
        ax.plot(ORIGIN[1], ORIGIN[0], 'o', ms=8, mfc='#111', mec='white', mew=2)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect(aspect)
        ax.set_axis_off()
        ax.text(0.015, 0.985, label, transform=ax.transAxes,
                ha='left', va='top', fontsize=22, fontweight='bold', color='#222',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='none', alpha=0.85))
        if overview:
            colorbar(fig, ax)
        credit(ax)
        return fig, zone, err

    # one palette per view, from a frame with every color in it: basemap, ramp, outlines, the green edge
    palettes = {}
    for tag in ('exact', 'iso'):
        fig, _, _ = draw(tag, exact)
        palettes[tag] = shared_palette(fig, dpi=150)
        plt.close(fig)
    for tag, descs in frames:
        fig, zone, err = draw(tag, descs)
        palette = palettes['exact' if descs is None or tag == 'exact' else 'iso']
        save(fig, OUT / f'{case.prefix}_{tag}.png', dpi=150, palette=palette)
        plt.close(fig)
        if descs is not None:
            lam = tag if isinstance(tag, str) else f'lam={LAMS[tag]:g}'
            coco = descs['cocompact']
            print(f'  {lam}: compacted {len(zone):,} cells, {err:.2f}% | '
                  f'co-compacted {len(coco):,} tokens, {kept(case, coco, weights, iso):.2f}%')


CREDIT = f"{TILES['attribution']} · drive times from OpenStreetMap data © OpenStreetMap contributors (ODbL)"


def credit(ax):
    '''The tile provider's and the data's credit, in the lower-left corner of the map.'''
    ax.text(0.005, 0.005, CREDIT, transform=ax.transAxes, ha='left', va='bottom', fontsize=8, color='#555',
            bbox=dict(boxstyle='square,pad=0.3', fc='white', ec='none', alpha=0.8))


def big_unreachable(minutes, least=400):
    '''The unreachable cells that lie in a connected unreachable blob of at least `least`
    cells: the river and the harbor, not the parks and cemeteries. H3 only.'''
    from h3.api import basic_int as h3
    todo = {c for c, t in minutes.items() if t is None}
    sea = set()
    while todo:
        blob = {todo.pop()}
        queue = deque(blob)
        while queue:
            for n in h3.grid_ring(queue.popleft(), 1):
                if n in todo:
                    todo.remove(n)
                    blob.add(n)
                    queue.append(n)
        if len(blob) >= least:
            sea |= blob
    return sea


def closer(case, view, tiles, minutes, iso, exact):
    '''A closer look at the exact isochrone: an overview with three numbered boxes
    ({prefix}_closer.png) and a zoom into each ({prefix}_closer_{1,2,3}.png), the
    cells colored by ETA, the compacted outlines and the green edge, and the
    minutes written on the cells that matter. The spots, each a res r-2 cell:

    1. nearly full: every missing cell is just over T, so adding them completes groups
    2. shoreline: the missing cells are all water, unreachable, and the shore is a mess of
       compacted cells; add the water and the whole group is one cell
    3. barely in: a few scattered cells just under T, each its own compacted cell; drop them
       all and the group is empty, giving up a minute or two of fidelity
    '''
    m, r = case.m, case.r
    groups = defaultdict(list)
    for c in minutes:
        groups[m.cell_to_parent(c, r - 2)].append(c)
    whole = {p: kids for p, kids in groups.items() if len(kids) == 49}   # fully inside the universe
    missing = {p: [c for c in kids if c not in iso] for p, kids in whole.items()}
    over = [p for p, gone in missing.items()
            if 0 < len(gone) <= 4 and all(minutes[c] is not None and minutes[c] <= T + 1.5 for c in gone)]
    sea = big_unreachable(minutes)   # water: the unreachable cells in a large connected blob
    water = [p for p, gone in missing.items() if 10 <= len(gone) <= 35 and all(c in sea for c in gone)]
    pieces = Counter(m.cell_to_parent(c, r - 2) for c in exact['compact'])   # compacted cells per group
    # barely in: the group that is cheapest to empty, per compacted cell saved
    slack = {p: sum(T - minutes[c] for c in kids if c in iso) for p, kids in whole.items()}
    barely = [p for p in whole if pieces[p] >= 8 and len(missing[p]) < 49]
    spots = [min(over, key=lambda p: len(missing[p])), max(water, key=lambda p: pieces[p]),
             min(barely, key=lambda p: slack[p] / pieces[p])]
    polys, colors = field_layer(case, minutes)
    edge = region(m, iso)

    # the overview: the exact isochrone with the three boxes
    xlim, ylim, aspect, figsize = view
    img, extent = tiles
    fig = plt.figure(figsize=figsize)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.imshow(img, extent=extent, interpolation='bilinear', zorder=0)
    ax.add_collection(PolyCollection(polys, facecolors=colors, edgecolors='face', lw=0.2, alpha=0.75))
    outline(ax, edge, color=NEON, lw=2.5, solid_joinstyle='round')
    windows = []
    for k, p in enumerate(spots, start=1):
        x0, y0, x1, y1 = footprint(m, p, r).bounds
        pad = 0.5 * (x1 - x0)
        box = shapely.box(x0 - pad, y0 - pad * aspect, x1 + pad, y1 + pad * aspect)
        windows.append(box)
        outline(ax, box, color='#111', lw=3.5)
        ax.text(box.bounds[0], box.bounds[3], f'{k}', ha='right', va='bottom', fontsize=24, fontweight='bold',
                color='white', bbox=dict(boxstyle='square,pad=0.2', fc='#111', ec='none'))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect(aspect)
    credit(ax)
    ax.set_axis_off()
    save(fig, OUT / f'{case.prefix}_closer.png', dpi=150, colors=256)
    plt.close(fig)

    # the zooms: higher-zoom tiles, the compacted outlines, and the minutes that matter
    for k, (p, box) in enumerate(zip(spots, windows), start=1):
        zx, zy, zaspect, zsize = frame([box], pad=0.0, width=8)
        zimg, zext = basemap(zx, zy, zoom=15)
        fig = plt.figure(figsize=zsize)
        ax = fig.add_axes((0, 0, 1, 1))
        ax.imshow(zimg, extent=zext, interpolation='bilinear', zorder=0)
        ax.add_collection(PolyCollection(polys, facecolors=colors, edgecolors='face', lw=0.2, alpha=0.75))
        for t in exact['compact']:
            outline(ax, footprint(m, t, r), color='#111', lw=1.5, solid_joinstyle='round')
        outline(ax, edge, color=NEON, lw=4, solid_joinstyle='round')
        shown = {1: missing[p], 2: [], 3: [c for c in whole[p] if c in exact['compact']]}[k]
        for c in shown:
            lat, lng = m.cell_to_latlng(c)
            text = '–' if minutes[c] is None else f'{minutes[c]:.1f}'
            ax.text(lng, lat, text, ha='center', va='center', fontsize=9, fontweight='bold', color='#111')
        ax.set_xlim(*zx)
        ax.set_ylim(*zy)
        ax.set_aspect(zaspect)
        credit(ax)
        ax.set_axis_off()
        save(fig, OUT / f'{case.prefix}_closer_{k}.png', dpi=150, colors=256)
        plt.close(fig)
        gone = missing[p]
        print(f'  closer {k}: res-{r - 2} cell {p:x}, {len(whole[p]) - len(gone)} of 49 in, '
              f'{len(gone)} missing, {pieces[p]} compacted cells cover the group')


def colorbar(fig, ax):
    '''The field's scale, minutes - T, in the map's top-right corner.'''
    cax = ax.inset_axes((0.64, 0.955, 0.32, 0.022))
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=NORM, cmap=RAMP), cax=cax, orientation='horizontal')
    bar.set_ticks([-T, -10, 0, 10, T], labels=['−20', '−10', '0', '+10', '+20'])
    bar.ax.tick_params(labelsize=12)
    bar.outline.set_visible(False)


def frontier(case, curves, exact):
    '''Fidelity kept vs description size for the compacted and co-compacted
    sizes (the raw cell count needs thousands of cells and is left out), with
    the hero number: how much smaller the co-compacted zone keeping 99% is
    than the co-compacted isochrone.'''
    fig, ax = plt.subplots(figsize=(10, 6))
    for size in ('compact', 'cocompact'):
        xs, ys = zip(*([(len(exact[size]), 100.0)] + curves[size]))
        ax.plot(xs, ys, color=COLORS[size], lw=2.5, marker='o', ms=4, label=SIZES[size])
        if size == 'compact':   # in case someone asks: co-compacted only after optimizing
            xs, ys = zip(*([(len(exact['cocompact']), 100.0)] + curves['post']))
            ax.plot(xs, ys, color=COLORS['cocompact'], lw=1.8, ls='--',
                    label='compacted, then co-compacted')
    full = len(exact['cocompact'])
    hero, k = min((x, k) for x, k in curves['cocompact'] if k >= 99)
    ax.plot([full, hero], [100, k], 'o', ms=9, mfc='white', mec=COLORS['cocompact'], mew=2.5)
    ax.annotate(f'the co-compacted isochrone\nhas {full:,} cells', (full, 100), (70, -62),
                textcoords='offset points', ha='right', fontsize=12, color='#333',
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.5))
    ax.annotate(f'{hero:,} cells at {k:.1f}% fidelity:\n{full / hero:.1f}x smaller', (hero, k), (40, -70),
                textcoords='offset points', fontsize=14, fontweight='bold', color='#333',
                arrowprops=dict(arrowstyle='->', color='#333', lw=1.5))
    ax.set_xscale('log')
    ax.set_xlabel('description size (cells)', fontsize=13)
    ax.set_ylabel('% fidelity (of the most possible, the isochrone)', fontsize=13)
    ax.set_ylim(95, 100)
    ax.grid(color='#e6e6e2', lw=0.8)
    for side in ('top', 'right'):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, fontsize=13, loc='lower right')
    fig.text(0.99, 0.01, 'drive times © OpenStreetMap contributors (ODbL)',
             ha='right', va='bottom', fontsize=8, color='#666')
    ax.tick_params(labelsize=11)
    path = OUT / f'{case.prefix}_frontier.png'
    save(fig, path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f'  wrote {path}')


def budgets(curves, exact):
    print('\nsmallest description keeping a share of the fidelity:')
    for b in (99.9, 99.7, 99.5, 99.0, 98.0, 96.0):
        n = {size: min((x for x, k in curves[size] if k >= b), default=None) for size in curves}
        print(f'  >= {b:4.1f}%: cells {n["cells"]}, compacted {n["compact"]}, '
              f'then co-compacted {n["post"]}, co-compacted {n["cocompact"]}'
              f'  | encoding {n["compact"] / n["post"]:.2f}x, awareness {n["post"] / n["cocompact"]:.2f}x, '
              f'{len(exact["cocompact"]) / n["cocompact"]:.1f}x smaller than the co-compacted isochrone')


def run(case, view, tiles):
    m = case.m
    minutes = load_field(case)
    weights = {c: 0.0 if t is None else T - t for c, t in minutes.items()}
    iso = {c for c, t in minutes.items() if t is not None and t <= T}
    exact = {'cells': iso, 'compact': m.compact(iso), 'cocompact': m.cocompact(iso)}
    print(f'\n{case.name} r = {case.r}: {len(minutes):,} cells in the universe; '
          f'I_{T:g}: {len(iso):,} cells, {len(exact["compact"]):,} compacted, {len(exact["cocompact"]):,} tokens')
    if case.name == 'h3':
        closer(case, view, tiles, minutes, iso, exact)
    movie(case, view, tiles, weights, minutes, iso, exact)
    curves = sweep(case, weights, iso)
    frontier(case, curves, exact)
    budgets(curves, exact)


def main():
    view = frame([shapely.box(*UNIVERSE)], pad=0.08)
    tiles = basemap(*view[:2])   # both systems share the view, so fetch the tiles once
    for case in CASES:
        run(case, view, tiles)


if __name__ == '__main__':
    main()
