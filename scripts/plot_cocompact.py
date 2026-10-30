'''Co-compacted bags, built up one layer of nesting at a time.

A fine cell is in the set when an odd number of its ancestors (itself
included) are tokens in the bag. Each figure fills cells as in (green) or
carved out (hatched: covered by an even number of tokens), and outlines each
token's footprint F_r(c).

Each sequence adds the bag's tokens by nesting depth: a token's depth is 1
plus the number of its ancestors that are also tokens. Step 1 adds the
top-level tokens (whatever their resolution), step 2 takes away the tokens
nested in those, step 3 adds back the next layer, and so on. Step k draws the
set decoded from the tokens of depth <= k, with that step's new tokens
outlined in black and earlier ones in grey. The last step, `all`, is the
composite: every outline the same.

XOR doesn't care about order, so this gives the same set as the query's walk
up the ancestors by resolution; it just groups the tokens so that each step
only adds or only takes away.

- stuck: one H3 cell with all of its grandchildren but one. Compaction
  needs 12 cells (6 full children, plus 6 grandchildren of the seventh);
  "the cell, minus that grandchild" is 2. Drawn as the cells, then the
  compacted set, then the bag. This is the pitch for co-compaction.
- phantom: one H3 res-5 cell P with three of its children as tokens: two
  neighbors and the center. Together their outlines trace the full outline of
  a fourth child, d, which is not a token. Counting loops says d is carved
  out; counting d's tokened ancestors (just P) says it's in.
- ct: Connecticut, in H3 (r = 7) and S2 (r = 12), four steps each.

    uv run scripts/plot_cocompact.py
'''
from collections import Counter

from pathlib import Path

import h3.api.basic_int as _h3
import matplotlib.pyplot as plt
import shapely
import shapely.affinity

from dggs_sets.plot import CARVED, IN, NEW, TOKEN, draw_bag, footprint, frame, nesting, patch, save
from dggs_sets import data, h3, s2
from plot_query import CELL_RES, LAT, LNG

OUT = Path(__file__).parent.parent / 'talk' / 'figs'


def sequence(name, m, bag, r, boundary=None):
    '''Write one figure per nesting depth, plus the composite.'''
    depth_of = nesting(m.grid, bag)
    levels = sorted(set(depth_of.values()))
    view = frame([footprint(m, t, r) for t in bag] + ([boundary] if boundary else []))
    for k in levels:
        tokens = {t for t in bag if depth_of[t] <= k}
        draw_bag(OUT / f'coco_{name}_step{k}.png', m, tokens, r, view,
                 is_new=lambda t: depth_of[t] == k, boundary=boundary)
    draw_bag(OUT / f'coco_{name}_all.png', m, bag, r, view, boundary=boundary)


def simple():
    '''A three-token bag on the hierarchy slides' cell: add the res-5 cell, take
    away one child, add back one of that child's children. The set itself,
    one figure per nesting depth, and the composite.'''
    r = CELL_RES + 2
    P = h3.latlng_to_cell(LAT, LNG, CELL_RES)
    child = max(h3.grid.children(P))
    grandchild = max(h3.grid.children(child))
    bag = {P, child, grandchild}
    cells = h3.uncompact(bag, r)
    assert len(cells) == 43 and h3.cocompact(cells) == bag
    print(f'simple: {len(cells)} cells, {len(h3.compact(cells))} compacted, {len(bag)} in the bag')
    view = frame([footprint(h3, P, r)])
    draw_bag(OUT / 'coco_simple_set.png', h3, cells, r, view)
    draw_bag(OUT / 'coco_simple_compact.png', h3, h3.compact(cells), r, view)
    sequence('simple', h3, bag, r)


def stuck():
    r = 7
    P = h3.latlng_to_cell(41.8, -72.3, r - 2)
    child = max(h3.grid.children(P))         # an outer child ...
    missing = max(h3.grid.children(child))   # ... and an outer grandchild of it
    cells = set(h3.uncompact({P}, r)) - {missing}
    compacted = h3.compact(cells)
    assert len(cells) == 48 and len(compacted) == 12
    assert h3.cocompact(cells) == {P, missing}
    print(f'stuck: {len(cells)} cells, {len(compacted)} compacted, 2 in the bag')
    # a wide frame, so the slide's corner note sits clear of the cells
    view = frame([shapely.affinity.scale(h3.footprint(P, r), 1.9, 1.25)])
    draw_bag(OUT / 'coco_stuck_cells.png', h3, cells, r, view)
    draw_bag(OUT / 'coco_stuck_compact.png', h3, compacted, r, view)
    draw_bag(OUT / 'coco_stuck_bag.png', h3, {P, missing}, r, view)


def ggc():
    '''All of one cell's great-grandchildren but one: the hierarchy slides' res-5
    cell, so the picture lines up with "Its great-grandchildren". 342 cells
    compact to 18 (6 children, 6 grandchildren, 6 great-grandchildren) and
    co-compact to 2.'''
    r = CELL_RES + 3
    P = h3.latlng_to_cell(LAT, LNG, CELL_RES)
    child = max(h3.grid.children(P))                   # an outer child, an outer grandchild of it,
    grandchild = max(h3.grid.children(child))          # and an outer great-grandchild of that
    missing = max(h3.grid.children(grandchild))
    cells = set(h3.uncompact({P}, r)) - {missing}
    compacted = h3.compact(cells)
    assert len(cells) == 342 and len(compacted) == 18
    assert h3.cocompact(cells) == {P, missing}
    print(f'ggc: {len(cells)} cells, {len(compacted)} compacted, 2 in the bag')
    view = frame([h3.footprint(P, r)], pad=0.08, width=8)
    gone = h3.cell_to_boundary(missing)   # hatched, so the hole shows
    draw_bag(OUT / 'coco_ggc_cells.png', h3, cells, r, view, hole=gone)
    draw_bag(OUT / 'coco_ggc_compact.png', h3, compacted, r, view, hole=gone)
    draw_bag(OUT / 'coco_ggc_bag.png', h3, {P, missing}, r, view)
    # the same two cells as their own hexagons: "parent, minus missing child"
    xlim, ylim, aspect, figsize = view
    fig, ax = plt.subplots(figsize=figsize)
    ax.add_patch(patch(h3.cell_to_boundary(P), fc=IN['fc'], ec=NEW, lw=TOKEN['lw']))
    ax.add_patch(patch(gone, **CARVED | dict(ec=NEW, lw=TOKEN['lw'])))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect(aspect)
    ax.set_axis_off()
    save(fig, OUT / 'coco_ggc_geo.png', dpi=200)
    plt.close(fig)
    print(f'  wrote {OUT / "coco_ggc_geo.png"}')


def phantom():
    r = 7
    P = h3.latlng_to_cell(41.8, -72.3, 5)
    c0 = _h3.cell_to_center_child(P, 6)
    outer = sorted(set(h3.grid.children(P)) - {c0})
    d = outer[0]
    foot = {k: h3.footprint(k, r) for k in outer}
    a, e = [k for k in outer if k != d and foot[k].intersection(foot[d]).length > 0]
    bag = {P, a, e, c0}
    # d's outline is fully traced by the other tokens' outlines
    lines = shapely.union_all([h3.footprint(t, r).boundary for t in bag])
    assert foot[d].boundary.difference(lines.buffer(1e-9)).length == 0
    # and this bag is minimal: it ties with keeping the other four children
    assert len(h3.cocompact(h3.uncompact(bag, r))) == len(bag)
    print(f'phantom: P res 5, d = {d:x} is outlined but not a token')
    sequence('phantom', h3, bag, r)


def ct():
    geom = data.states()['Connecticut']
    for name, m, r in [('h3', h3, 7), ('s2', s2, 12)]:
        cells = m.polygon_to_cells(geom, r)
        bag = m.cocompact(cells)
        print(f'ct {name} r {r}: {len(cells)} cells, {len(m.compact(cells))} compacted, {len(bag)} tokens,',
              'by depth', dict(sorted(Counter(nesting(m.grid, bag).values()).items())))
        sequence(f'ct_{name}_{r}', m, bag, r, boundary=geom)


def main():
    plt.rcParams['hatch.linewidth'] = 0.6
    simple()
    stuck()
    ggc()
    phantom()
    ct()


if __name__ == '__main__':
    main()
