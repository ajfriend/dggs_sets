'''Compaction and co-compaction, over a cell tree.

A "bag" is a plain set of cells, possibly at mixed resolutions and possibly
nested. A fine cell is in the set a bag describes iff an odd number of its
ancestors (itself included) appear in the bag. Every set of cells is a valid
bag; standard compaction is the special case with no nesting, so one
decoder (`uncompact`) handles both.

`compact` and `cocompact` walk the tree above `cells`: at each parent `p`,
combine its children's answers. Popping each child's answer as its parent
uses it leaves only the roots' answers at the end.
'''
from collections import Counter

from .tree import cell_tree, descendants


def compact(grid, cells):
    '''Standard compaction of `cells` (all at one resolution): replace each
    complete sibling group by its parent.'''
    zone = {c: {c} for c in cells}
    for p, kids in cell_tree(grid, cells):
        kid_zone = _union(zone.pop(k, set()) for k in kids)
        zone[p] = {p} if kid_zone == set(kids) else kid_zone   # every child whole: merge
    return _union(zone.values())


def cocompact(grid, cells):
    '''The smallest bag describing `cells` (all at one resolution).

    Each cell keeps two answers: the smallest bag for its subtree as is
    (exactly the wanted cells), and flipped (exactly the unwanted ones, which
    is what it needs under a token higher up). A parent either takes its
    children's answers, or becomes a token and swaps them.
    '''
    as_is = {c: {c} for c in cells}
    flipped = {c: set() for c in cells}
    for p, kids in cell_tree(grid, cells):
        kid_as_is = _union(as_is.pop(k, set()) for k in kids)       # a child with nothing wanted: free
        kid_flipped = _union(flipped.pop(k, {k}) for k in kids)     # ...or a token to turn it all out
        as_is[p] = _smaller(kid_as_is, kid_flipped | {p})
        flipped[p] = _smaller(kid_flipped, kid_as_is | {p})
    return _union(as_is.values())


def uncompact(grid, bag, res):
    '''Parity decode: expand every cell to `res` and keep the odd counts.
    `bag` may hold a cell more than once (a list, say): duplicates cancel in pairs.'''
    counts = Counter(k for c in bag for k in descendants(grid, c, res))
    return {c for c, n in counts.items() if n % 2}


def contains(grid, bag, cell):
    '''Point query: is `cell` covered by an odd number of bag entries?'''
    n = cell in bag
    for _ in range(grid.resolution(cell)):
        cell = grid.parent(cell)
        n += cell in bag
    return n % 2 == 1


def _union(sets):
    return set().union(*sets)


def _smaller(a, b):
    return min(a, b, key=len)   # ties: prefer a
