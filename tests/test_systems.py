'''Per-DGGS round trips on every US state, and cross-checks against native compaction.'''
import a5
import pytest
import s2geometry as s2
from h3.api import basic_int as h3

from dggs_sets import SYSTEMS, data

# coarse but non-trivial resolutions (~250-500 km^2 cells) to keep tests fast
RES = {'h3': 5, 's2': 9, 'a5': 8}

NATIVE_COMPACT = {
    'h3': lambda cells: set(h3.compact_cells(list(cells))),
    's2': lambda cells: {c.id() for c in s2.S2CellUnion([s2.S2CellId(c) for c in cells]).cell_ids()},
    'a5': lambda cells: {c for c in a5.compact(list(cells)) if not a5.is_compaction_marker(c)},
}


@pytest.fixture(scope='module', params=sorted(SYSTEMS))
def system(request):
    name = request.param
    return name, SYSTEMS[name], data.cellsets(SYSTEMS[name], data.states(), RES[name])


def test_roundtrip_all_states(system):
    name, m, cells_by_state = system
    res = RES[name]
    for state, cells in cells_by_state.items():
        c, cc = m.compact(cells), m.cocompact(cells)
        assert m.uncompact(c, res) == cells, state
        assert m.uncompact(cc, res) == cells, state
        assert len(cc) <= len(c), state


def test_matches_native_compact(system):
    name, m, cells_by_state = system
    for state, cells in cells_by_state.items():
        assert m.compact(cells) == NATIVE_COMPACT[name](cells), state


def test_contains(system):
    name, m, cells_by_state = system
    cells = cells_by_state['Maryland']
    # wanted cells plus their unwanted siblings
    probe = {k for c in cells for k in m.grid.children(m.grid.parent(c))}
    bag = m.cocompact(cells)
    for c in probe:
        assert m.contains(bag, c) == (c in cells)


CELL_AREA_KM2 = {
    'h3': lambda c: h3.cell_area(c, 'km^2'),
    's2': lambda c: s2.S2Cell(s2.S2CellId(c)).ExactArea() * 6371.0088**2,
    'a5': lambda c: a5.cell_area(a5.get_resolution(c)) / 1e6,
}


@pytest.mark.parametrize('name', sorted(SYSTEMS))
def test_polygon_to_cells_area(name):
    '''Center-fill area should match Colorado's area (~269,600 km^2) to ~1%.'''
    m = SYSTEMS[name]
    cells = m.polygon_to_cells(data.states()['Colorado'], RES[name] + 2)
    area = sum(CELL_AREA_KM2[name](c) for c in cells)
    assert area == pytest.approx(269_600, rel=0.01)


def test_s2_bit_hierarchy_matches_bindings():
    import random

    from dggs_sets import s2 as xs2

    rng = random.Random(0)
    for _ in range(2000):
        ll = s2.S2LatLng.FromDegrees(rng.uniform(-90, 90), rng.uniform(-180, 180))
        cid = s2.S2CellId(ll).parent(rng.randint(1, 29))
        c = cid.id()
        assert xs2.grid.resolution(c) == cid.level()
        assert xs2.grid.parent(c) == cid.parent().id()
        assert xs2.grid.children(c) == [cid.child(i).id() for i in range(4)]
    # face cells, one per cube face
    for lat, lng in [(0, 0), (0, 90), (90, 0), (0, 180), (0, -90), (-90, 0)]:
        c = s2.S2CellId(s2.S2LatLng.FromDegrees(lat, lng)).parent(0)
        assert xs2.grid.resolution(c.id()) == 0
        assert xs2.grid.children(c.id()) == [c.child(i).id() for i in range(4)]


@pytest.mark.parametrize('name', sorted(SYSTEMS))
def test_footprint(name):
    '''A footprint is exactly its descendants' area; it equals the cell only in S2.'''
    m = SYSTEMS[name]
    cell = next(iter(m.polygon_to_cells(data.states()['Connecticut'], RES[name])))
    res = RES[name] + 2
    f = m.footprint(cell, res)
    kids = m.uncompact({cell}, res)
    assert f.area == pytest.approx(sum(m.cell_to_boundary(k).area for k in kids), rel=1e-6)
    g = m.cell_to_boundary(cell)
    mismatch = g.symmetric_difference(f).area / g.area
    if name == 's2':
        # exact in theory; the slack is chord sag from drawing geodesic edges as segments
        assert mismatch < 1e-4
    else:
        assert mismatch > 0.05


@pytest.mark.parametrize('name', sorted(SYSTEMS))
def test_cell_to_latlng_round_trips(name):
    m = SYSTEMS[name]
    for lat, lng in [(40.69, -73.99), (-33.9, 151.2), (64.1, -21.9)]:
        cell = m.latlng_to_cell(lat, lng, 9)
        assert m.latlng_to_cell(*m.cell_to_latlng(cell), 9) == cell
