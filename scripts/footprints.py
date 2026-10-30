'''How far is a cell's own polygon G(c) from its footprint F_r(c)?

For random cells, compare the geometric cell with the area covered by its
descendants `depth` levels down:

- IoU: area(G ∩ F) / area(G ∪ F); 1 means identical
- mismatch: area(G Δ F) / area(G), the area you'd draw wrong (gap +
  overlap) if you used the geometric cell instead of the footprint

Areas are planar in lng/lat, which is fine for ratios within a small cell.
Cells are sampled away from the poles and the antimeridian.

    uv run scripts/footprints.py
'''
import random
import statistics

from tabulate import tabulate

from dggs_sets import SYSTEMS

N = 100
SEED = 0
# a mid resolution with ~100-300 km^2 cells, and how deep to go
# (H3 is aperture 7, so it gets fewer levels for a similar descendant count)
RES = {'h3': 5, 's2': 10, 'a5': 9}
DEPTHS = {'h3': [1, 2, 4], 's2': [1, 2, 5], 'a5': [1, 2, 5]}

def sample(m, res):
    rng = random.Random(SEED)
    cells = set()
    while len(cells) < N:
        lng, lat = rng.uniform(-170, 170), rng.uniform(-60, 60)
        cells.add(m.latlng_to_cell(lat, lng, res))
    return sorted(cells)


def main():
    rows = []
    for name, m in SYSTEMS.items():
        res = RES[name]
        cells = sample(m, res)
        for depth in DEPTHS[name]:
            ious, mismatches = [], []
            for c in cells:
                g = m.cell_to_boundary(c)
                f = m.footprint(c, res + depth)
                ious.append(g.intersection(f).area / g.union(f).area)
                mismatches.append(g.symmetric_difference(f).area / g.area)
            rows.append([
                name, res, depth, f'{statistics.mean(ious):.3f}',
                f'{100 * statistics.mean(mismatches):.1f}%',
                f'{100 * min(mismatches):.1f}–{100 * max(mismatches):.1f}%',
            ])
    print(tabulate(rows, headers=['system', 'res', 'depth', 'mean IoU', 'mean mismatch', 'mismatch range'],
                   tablefmt='github'))


if __name__ == '__main__':
    main()
