'''Compression statistics for compaction and XOR co-compaction on US states,
across H3, S2 and A5.

Each system uses one resolution for every state, chosen so average cell
areas are close (~5 km^2; A5's aperture 4 has nothing closer than ~8 km^2).

    uv run scripts/stats.py
'''
import csv
from pathlib import Path

from tabulate import tabulate

from dggs_sets import SYSTEMS, data

RES = {'h3': 7, 's2': 12, 'a5': 11}
OUT = Path(__file__).parent / 'out' / 'stats.csv'


def run():
    states = data.states()
    rows = []
    for name, m in SYSTEMS.items():
        res = RES[name]
        for state, geom in sorted(states.items()):
            cells = m.polygon_to_cells(geom, res)
            c, cc = m.compact(cells), m.cocompact(cells)
            assert m.uncompact(cc, res) == cells, (name, state)
            rows.append(dict(
                system=name, state=state, res=res,
                cells=len(cells), compact=len(c), cocompact=len(cc),
            ))
    return rows


def pct(a, b):
    '''`a` as a percentage of `b`.'''
    return f'{100 * a / b:.2f}%'


def main():
    rows = run()
    OUT.parent.mkdir(exist_ok=True)
    with OUT.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    # each state is compacted on its own; the counts are then summed over states
    summary = []
    for name, m in SYSTEMS.items():
        rs = [r for r in rows if r['system'] == name]
        cells, comp, coco = (sum(r[k] for r in rs) for k in ('cells', 'compact', 'cocompact'))
        summary.append([
            name, RES[name], f'{m.avg_cell_area_km2(RES[name]):.2f}',
            cells, pct(comp, cells), pct(coco, cells), f'{comp / coco:.2f}×',
        ])
    print('\n## Summed over US states (each state compacted separately)\n')
    print(tabulate(summary, headers=['system', 'res', 'avg km²', 'cells', 'compact (% of cells)',
                                     'cocompact (% of cells)', 'cocompact smaller by'],
                   tablefmt='github', intfmt=','))
    print(f'\nwrote {OUT}')


if __name__ == '__main__':
    main()
