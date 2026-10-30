'''Figures for the co-compaction encoder slides.

The encoder on one S2 cell, drawn as a square with its descendants 3 levels
down (an 8 x 8 quadtree), one level per figure. Each block is labelled with
its two costs, "as is · flipped":

- as is: the fewest tokens for exactly the wanted leaves in the block
- flipped: the fewest tokens for exactly the unwanted ones (what's needed
  under a token higher up, which flips everything below it)

A leaf costs 1 · 0 if wanted, 0 · 1 if not. A block either sums its
children's costs, or takes itself as a token (+1) and uses its children's
costs the other way round. The last figure draws the resulting bag.

    uv run scripts/plot_encoder.py
'''
from collections import Counter
from functools import cache

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from dggs_sets.plot import CARVED, IN, NEW, depths, nesting, save
from dggs_sets.core.compaction import cocompact, compact, uncompact
from dggs_sets.core.tree import Grid, cell_tree

OUT = Path(__file__).parent.parent / 'talk' / 'figs'

DEPTH = 3   # toy quadtree: leaves at level 3, so 8 x 8 of them


# toy quadtree: a cell is (level, i, j); level 0 is the root
TOY = Grid(
    parent=lambda c: (c[0] - 1, c[1] // 2, c[2] // 2),
    children=lambda c: [(c[0] + 1, 2 * c[1] + di, 2 * c[2] + dj) for di in (0, 1) for dj in (0, 1)],
    resolution=lambda c: c[0],
)
ROOT = (0, 0, 0)
N = 2 ** DEPTH


def toy_cells():
    '''A blob: a disk with a bite out of it and a stray cell.'''
    cells = set()
    for i in range(N):
        for j in range(N):
            x, y = i + 0.5, j + 0.5
            if (x - 4.2) ** 2 + (y - 4.0) ** 2 < 3.6 ** 2 and not (x > 5 and y > 5.5):
                cells.add((DEPTH, i, j))
    return cells | {(DEPTH, 7, 7)}


def toy_costs(cells):
    @cache
    def costs(p):
        if p[0] == DEPTH:
            return (1, 0) if p in cells else (0, 1)
        a = f = 0
        for k in TOY.children(p):
            ka, kf = costs(k)
            a, f = a + ka, f + kf
        return min(a, 1 + f), min(f, 1 + a)
    return costs


def toy_axes():
    fig = plt.figure(figsize=(9, 9))
    ax = fig.add_axes((0.02, 0.02, 0.96, 0.96))
    ax.set_xlim(-0.1, N + 0.1)
    ax.set_ylim(-0.1, N + 0.1)
    ax.set_aspect(1)
    ax.set_axis_off()
    return fig, ax


def square(c):
    size = 2 ** (DEPTH - c[0])
    return c[1] * size, c[2] * size, size


def toy_leaves(ax, cells):
    for i in range(N):
        for j in range(N):
            if (DEPTH, i, j) in cells:
                ax.add_patch(Rectangle((i, j), 1, 1, **IN))
            ax.add_patch(Rectangle((i, j), 1, 1, fc='none', ec='#ddd', lw=0.6))


def toy():
    cells = toy_cells()
    costs = toy_costs(cells)
    tree = cell_tree(TOY, cells)
    bag = cocompact(tree, cells)
    assert costs(ROOT)[0] == len(bag), (costs(ROOT), len(bag))
    assert uncompact(TOY, bag, DEPTH) == cells
    compacted = compact(tree, cells)
    nest = Counter(nesting(TOY, bag).values())
    print(f'toy: {len(cells)} leaves, {len(compacted)} compacted, {len(bag)} tokens,',
          'by depth', dict(sorted(nest.items())), '; root costs', costs(ROOT))

    # 0: the leaves
    fig, ax = toy_axes()
    toy_leaves(ax, cells)
    save(fig, OUT / 'encoder_toy_0.png')
    plt.close(fig)

    # 1..DEPTH: label each block at one level, finest blocks first
    for step, level in enumerate(range(DEPTH - 1, -1, -1), start=1):
        fig, ax = toy_axes()
        toy_leaves(ax, cells)
        for i in range(2 ** level):
            for j in range(2 ** level):
                c = (level, i, j)
                x, y, size = square(c)
                ax.add_patch(Rectangle((x, y), size, size, fc='none', ec=NEW, lw=2))
                a, f = costs(c)
                ax.text(x + size / 2, y + size / 2, f'{a} · {f}', ha='center', va='center',
                        fontsize=30 if level else 44, fontweight='bold', color='#222',
                        bbox=dict(boxstyle='round,pad=0.25', fc='white', ec='none', alpha=0.9))
        save(fig, OUT / f'encoder_toy_{step}.png')
        plt.close(fig)

    # last: the bag
    fig, ax = toy_axes()
    for (_, i, j), n in depths(TOY, bag, DEPTH).items():
        ax.add_patch(Rectangle((i, j), 1, 1, **(IN if n % 2 else CARVED)))
    for t in sorted(bag):
        x, y, size = square(t)
        ax.add_patch(Rectangle((x, y), size, size, fc='none', ec=NEW, lw=2))
    save(fig, OUT / f'encoder_toy_{DEPTH + 1}.png')
    plt.close(fig)
    print(f'  wrote {OUT}/encoder_toy_0..{DEPTH + 1}.png')


def main():
    plt.rcParams['hatch.linewidth'] = 0.6
    toy()


if __name__ == '__main__':
    main()
