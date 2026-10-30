'''Run the code on the membership-query slides (talk/index.qmd).

Every ```{.python check="..."} block is pulled out of the deck and executed
against real cellsets (US states, plus an overlapping "New England" cellset)
in each DGGS, then checked against brute-force membership.
'''
import random
import re
from collections import defaultdict
from functools import cache
from pathlib import Path

import pytest

from dggs_sets import SYSTEMS, data

DECK = Path(__file__).parent.parent / 'talk' / 'index.qmd'
RES = {'h3': 5, 's2': 9, 'a5': 8}
NEW_ENGLAND = ['Maine', 'New Hampshire', 'Vermont', 'Massachusetts', 'Rhode Island', 'Connecticut']


def blocks():
    src = DECK.read_text()
    return dict(re.findall(r'^```\{\.python check="(\w+)"[^}]*\}\n(.*?)^```', src, re.S | re.M))


BLOCKS = blocks()


def run(*names, **ns):
    given = dict(ns)
    ns |= {'defaultdict': defaultdict}
    for name in names:
        exec(BLOCKS[name], ns)
        if 'cellsets' in given:   # a slide may show a toy `cellsets` literal; its query runs on the real one
            ns['cellsets'] = given['cellsets']
    return ns


@pytest.fixture(scope='module', params=sorted(SYSTEMS))
def setup(request):
    name = request.param
    m, r = SYSTEMS[name], RES[name]
    states = data.cellsets(m, data.states(), r)
    cellsets = states | {'New England': set().union(*(states[s] for s in NEW_ENGLAND))}
    # the slide code walks the same ancestors once per cellset, so cache the lookups
    env = dict(r=r, latlng_to_cell=cache(m.latlng_to_cell), cell_to_parent=cache(m.cell_to_parent),
               compact=m.compact, cocompact=m.cocompact)
    rng = random.Random(0)
    points = [(rng.uniform(25, 49), rng.uniform(-125, -67)) for _ in range(3000)]
    points += [(rng.uniform(41, 47.5), rng.uniform(-73.7, -67)) for _ in range(2000)]   # New England
    return name, r, cellsets, env, points


def truth(cellsets, cell):
    return {name for name, cells in cellsets.items() if cell in cells}


def test_blocks_found():
    assert set(BLOCKS) == {'flat', 'flat_index', 'compact_index', 'bag_index'}


# each slide builds on the ones before: reverse_index from the flat-index slide,
# ancestors from the compacted-query slide
@pytest.mark.parametrize('blocks', [('flat',), ('flat_index',), ('flat_index', 'compact_index'),
                                    ('flat_index', 'compact_index', 'bag_index')])
def test_correct_queries(setup, blocks):
    _, r, cellsets, env, points = setup
    ns = run(*blocks, cellsets=cellsets, **env)
    hits = overlaps = 0
    for lat, lng in points:
        cell = env['latlng_to_cell'](lat, lng, r)
        want = truth(cellsets, cell)
        assert ns['containing'](cell) == want
        hits += bool(want)
        overlaps += len(want) > 1
    assert hits > 1000
    assert overlaps > 500   # cells in a New England state and in "New England"
