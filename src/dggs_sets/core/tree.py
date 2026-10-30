'''The cell hierarchy, as the algorithms see it: a tree of IDs.'''
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Grid:
    '''The only hierarchy primitives the algorithms need.'''
    parent: Callable[[int], int]            # immediate parent
    children: Callable[[int], list[int]]    # immediate children
    resolution: Callable[[int], int]


def cell_tree(grid, leaves):
    '''The tree above `leaves` (all at one resolution): every ancestor, paired
    with its children, finest level first, so children always come before
    their parent. Children include ones with no leaves under them.'''
    res = {grid.resolution(c) for c in leaves}
    assert len(res) <= 1, f'cells must share one resolution, got {sorted(res)}'
    pairs, level = [], set(leaves)
    for _ in range(res.pop() if res else 0):
        level = {grid.parent(c) for c in level}
        pairs += [(p, grid.children(p)) for p in level]
    return pairs


def descendants(grid, cell, res):
    '''`cell`'s descendants at `res` (the cell itself at its own resolution).'''
    level = [cell]
    for _ in range(res - grid.resolution(cell)):
        level = [k for c in level for k in grid.children(c)]
    return level


def cell_to_parent(grid, cell, res):
    '''The ancestor of `cell` at `res` (the cell itself at its own resolution).'''
    for _ in range(grid.resolution(cell) - res):
        cell = grid.parent(cell)
    return cell
