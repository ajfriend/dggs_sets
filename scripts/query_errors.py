'''How often does the geometric membership query get US states wrong?

Each state is compacted, and random points are looked up two ways:

- geometric: a cell per resolution with latlng_to_cell, looked up directly
- by ID: one cell at r, then its ancestors with cell_to_parent (always right)

A point counts as wrong if the two answers differ, out of the points that
either method places in some state.

    uv run scripts/query_errors.py
'''
import random
from collections import defaultdict

from tabulate import tabulate

from dggs_sets import SYSTEMS, data

RES = {'h3': 7, 's2': 12, 'a5': 11}
N = 100_000
SEED = 0


def main():
    rng = random.Random(SEED)
    points = [(rng.uniform(25, 49), rng.uniform(-125, -67)) for _ in range(N)]   # contiguous US box
    rows = []
    for name, m in SYSTEMS.items():
        r = RES[name]
        index = defaultdict(set)
        for state, cells in data.cellsets(m, data.states(), r).items():
            for c in m.compact(cells):
                index[c].add(state)

        counted = wrong = 0
        for lat, lng in points:
            geometric = {s for k in range(r + 1) for s in index.get(m.latlng_to_cell(lat, lng, k), ())}
            cell = m.latlng_to_cell(lat, lng, r)
            by_id = set(index.get(cell, ()))
            for _ in range(r):   # walk up the ancestors once
                cell = m.grid.parent(cell)
                by_id |= index.get(cell, set())
            if geometric or by_id:
                counted += 1
                wrong += geometric != by_id
        rows.append([name, r, f'{counted:,}', f'{wrong:,}', f'{100 * wrong / counted:.1f}%'])
    print(tabulate(rows, headers=['system', 'res', 'points in a state', 'wrong', 'wrong %'],
                   tablefmt='github'))


if __name__ == '__main__':
    main()
