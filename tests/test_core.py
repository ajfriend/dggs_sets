'''Core algorithms on a toy quadtree, plus H3 checks.'''
import random
from itertools import combinations

from h3.api import basic_int as h3

from dggs_sets import h3 as xh3
from dggs_sets.core.compaction import cocompact, compact, contains, uncompact
from dggs_sets.core.tree import Grid, cell_tree, descendants

# Toy quadtree: four roots 0b100..0b111; each level appends two bits.
TOY = Grid(
    parent=lambda c: c >> 2,
    children=lambda c: [c << 2 | i for i in range(4)],
    resolution=lambda c: (c.bit_length() - 3) // 2,
)
ROOTS = [4, 5, 6, 7]


def toy(f, cells, *args):
    '''Run a tree algorithm on the toy grid: build the tree above `cells`, then walk it.'''
    return f(cell_tree(TOY, cells), cells, *args)


def kids(c):
    return TOY.children(c)


def leaves(c, res):
    return set(descendants(TOY, c, res))


def test_full_siblings_collapse():
    S = set(kids(4))
    assert toy(compact, S) == {4}
    assert toy(cocompact, S) == {4}


def test_three_of_four():
    a, b, c, d = kids(4)
    S = {a, b, c}
    assert toy(compact, S) == S
    assert toy(cocompact, S) == {4, d}


def test_nested_three_levels():
    # root, minus one child, plus one grandchild back inside that child
    child = kids(4)[0]
    grandchild = kids(child)[0]
    S = (leaves(4, 2) - leaves(child, 2)) | {grandchild}
    bag = toy(cocompact, S)
    assert bag == {4, child, grandchild}
    assert uncompact(TOY, bag, 2) == S


def test_empty():
    assert toy(compact, set()) == set()
    assert toy(cocompact, set()) == set()


def _random_sets(n, res, seed=0):
    rng = random.Random(seed)
    universe = sorted(set().union(*(leaves(r, res) for r in ROOTS)))
    for _ in range(n):
        p = rng.random()
        yield {c for c in universe if rng.random() < p}


def test_random_roundtrip_and_contains():
    for S in _random_sets(50, res=4):
        c, cc = toy(compact, S), toy(cocompact, S)
        assert uncompact(TOY, c, 4) == S
        assert uncompact(TOY, cc, 4) == S
        assert len(cc) <= len(c)
        for leaf in leaves(4, 4):
            assert contains(TOY, cc, leaf) == (leaf in S)
            assert contains(TOY, c, leaf) == (leaf in S)


def test_minimal_by_brute_force():
    # one root, depth 2: 1 + 4 + 16 = 21 candidate tokens
    candidates = [4, *kids(4), *leaves(4, 2)]
    rng = random.Random(1)
    for _ in range(40):
        S = {c for c in leaves(4, 2) if rng.random() < rng.random()}
        bag = toy(cocompact, S)
        for k in range(len(bag)):
            for combo in combinations(candidates, k):
                assert uncompact(TOY, combo, 2) != S, (S, bag, combo)


def test_h3_cancel_across_two_levels():
    # 6 full children plus 4 of the last child's 7 kids: 46 cells.
    # Cheapest is the parent with the 3 missing grandchildren toggled
    # out (4 cells), not parent - last child + 4 grandchildren (6 cells).
    P = h3.cell_to_parent(h3.latlng_to_cell(40.69, -73.98, 1), 1)
    ks = sorted(h3.cell_to_children(P))
    gks = sorted(h3.cell_to_children(ks[6]))
    cells = {c for k in ks[:6] for c in h3.cell_to_children(k)}
    cells |= set(gks[:4])
    assert len(cells) == 46
    bag = xh3.cocompact(cells)
    assert bag == {P, *gks[4:]}
    assert xh3.uncompact(bag, 3) == cells


def test_h3_pentagon():
    pent = h3.get_pentagons(2)[0]
    S = set(h3.cell_to_children(pent, 4))
    S -= set(h3.cell_to_children(h3.cell_to_children(pent)[0], 4))
    bag = xh3.cocompact(S)
    assert xh3.uncompact(bag, 4) == S
    assert bag == {pent, h3.cell_to_children(pent)[0]}
