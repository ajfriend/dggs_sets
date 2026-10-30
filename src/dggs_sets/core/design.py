'''Compaction-aware set design, over a cell tree.

    design(tree, weights, lam, size)

chooses the set S of cells maximizing  sum(weights[c] for c in S) - lam * size(S),
and returns its description. Cells missing from `weights` are never chosen.
It is the same walk up `tree = cell_tree(grid, weights)` as `compact` and
`cocompact`, with each answer a (value, description) pair instead of just a
description.
'''
from math import inf

from .compaction import _union


def design(tree, weights, lam, size='cocompact'):
    '''The best set, described as cells, compacted cells, or a bag.'''
    if size == 'cells':
        return {c for c, w in weights.items() if w > lam}
    if size == 'compact':
        return design_compact(tree, weights, lam)
    if size == 'cocompact':
        return design_cocompact(tree, weights, lam)
    raise ValueError(f'size must be cells, compact or cocompact, not {size!r}')


def design_compact(tree, weights, lam):
    '''Each cell either takes its whole subtree as one cell, or leaves it to its children.'''
    full = dict(weights)   # summed weight of the subtree; -inf if any of it is missing
    best = {c: _better((0.0, set()), (v - lam, {c})) for c, v in weights.items()}
    for p, kids in tree:
        full[p] = sum(full.pop(k, -inf) for k in kids)
        kid_best = _total(best.pop(k, (0.0, set())) for k in kids)
        best[p] = _better(kid_best, (full[p] - lam, {p}))
    return _union(zone for _, zone in best.values())


def design_cocompact(tree, weights, lam):
    '''`cocompact` with weights. Each cell keeps its best answer as is (an even
    number of tokens above it) and flipped (odd), and a parent either takes its
    children's answers, or becomes a token (costing lam) and swaps them.'''
    as_is = {c: _better((0.0, set()), (v - lam, {c})) for c, v in weights.items()}
    flipped = {c: _better((v, set()), (-lam, {c})) for c, v in weights.items()}
    for p, kids in tree:
        kid_as_is = _total(as_is.pop(k, (0.0, set())) for k in kids)       # a missing child stays out for free
        kid_flipped = _total(flipped.pop(k, (-lam, {k})) for k in kids)    # ...or costs a token to turn it out
        as_is[p] = _better(kid_as_is, _token(kid_flipped, p, lam))
        flipped[p] = _better(kid_flipped, _token(kid_as_is, p, lam))
    return _union(bag for _, bag in as_is.values())


def _better(stay, change):
    return change if change[0] > stay[0] else stay   # ties: no change, so the fewer tokens


def _total(answers):
    answers = list(answers)
    return sum(v for v, _ in answers), _union(d for _, d in answers)


def _token(answer, cell, lam):
    value, desc = answer
    return value - lam, desc | {cell}
