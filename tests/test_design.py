'''design() against brute force on a small quadtree, and on real cells.'''
import random

import numpy as np
import pytest

from dggs_sets import h3 as xh3
from dggs_sets.core.compaction import cocompact, compact, uncompact
from dggs_sets.core.design import design
from dggs_sets import data

from test_core import TOY, leaves, toy

LEAVES = sorted(leaves(4, 2))   # one root, two levels down: 16 leaves
SIZE_OF = {
    'cells': len,
    'compact': lambda cells: len(toy(compact, cells)),
    'cocompact': lambda cells: len(toy(cocompact, cells)),
}


def _subset(mask):
    return {c for i, c in enumerate(LEAVES) if mask >> i & 1}


@pytest.fixture(scope='module')
def every_subset():
    '''Membership matrix and each size, for all 2**16 subsets.'''
    masks = range(2 ** len(LEAVES))
    member = np.array([[mask >> i & 1 for i in range(len(LEAVES))] for mask in masks], dtype=float)
    subsets = [_subset(m) for m in masks]
    sizes = {size: np.array([f(cells) for cells in subsets]) for size, f in SIZE_OF.items()}
    return member, sizes


def _value(weights, lam, size):
    '''design's objective value, its description, and the size it pays for.'''
    desc = toy(design, weights, lam, size)
    chosen = uncompact(TOY, desc, 2)
    n = SIZE_OF[size](chosen)
    return sum(weights[c] for c in chosen) - lam * n, desc, n


@pytest.mark.parametrize('size', SIZE_OF)
def test_design_is_optimal(every_subset, size):
    member, sizes = every_subset
    rng = random.Random(0)
    for _ in range(300):
        weights = {c: rng.uniform(-1, 1) for c in LEAVES}
        lam = rng.choice([0.0, 0.05, 0.2, 0.5, 1.0, 2.0])
        w = np.array([weights[c] for c in LEAVES])
        brute = (member @ w - lam * sizes[size]).max()
        value, desc, n = _value(weights, lam, size)
        assert value == pytest.approx(brute, abs=1e-9)
        if lam > 0:   # with any penalty, the description is also the smallest one
            assert len(desc) == n


def test_missing_cells_are_never_chosen():
    rng = random.Random(1)
    allowed = set(rng.sample(LEAVES, 10))
    for size in SIZE_OF:
        for lam in (0.0, 0.3, 1.0):
            weights = {c: rng.uniform(-1, 1) for c in allowed}
            assert uncompact(TOY, toy(design, weights, lam, size), 2) <= allowed


def test_cocompact_is_the_infinite_weight_case():
    '''With huge weights in and out of the set, design must return exactly
    the set, described by the smallest bag.'''
    cells = xh3.polygon_to_cells(data.states()['Connecticut'], 5)
    domain = xh3.uncompact({xh3.cell_to_parent(c, 2) for c in cells}, 5)
    weights = {c: 1e6 if c in cells else -1e6 for c in domain}
    bag = xh3.design(weights, 1.0, 'cocompact')
    assert xh3.uncompact(bag, 5) == cells
    assert len(bag) == len(xh3.cocompact(cells))
    zone = xh3.design(weights, 1.0, 'compact')
    assert zone == xh3.compact(cells)
