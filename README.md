# dggs_sets

The tutorial package for the FOSS4G talk *DGGS (Co-)Compaction and Set Design*: compaction, **co-compaction** and set design across three DGGSs, H3, S2 and A5, behind one interface. It's for learning from, not for production, and it isn't on PyPI: `uv add git+https://github.com/ajfriend/dggs_sets`, or clone it.

```python
from dggs_sets import h3, s2, a5, data   # same interface in each system

geom = data.states()['Maryland']
cells = s2.polygon_to_cells(geom, 12)   # set[int], cell center in polygon
bag = s2.cocompact(cells)               # set[int], minimal XOR bag
assert s2.uncompact(bag, 12) == cells
```

Each submodule provides these functions:

- `polygon_to_cells(geo, res)` takes any `__geo_interface__` (Polygon or MultiPolygon) and returns the cells whose centers lie inside it.
- `compact(cells)` is standard compaction: complete sibling groups are replaced by their parent.
- `cocompact(cells)` returns the smallest *bag* that describes `cells`.
- `uncompact(bag, res)` is the parity decoder. It works on the output of both `compact` and `cocompact`.
- `contains(bag, cell)` is a membership test: it counts how many of the cell's ancestors are in the bag and checks whether that number is odd.
- `design(weights, lam, size)` chooses the set S maximizing Σ weights[c] − lam · size(S), where `size` is `'cells'`, `'compact'` or `'cocompact'`. It returns S's description: the cells, the compacted cells, or the bag. Cells missing from `weights` are never chosen. Like `cocompact`, it takes one exact pass up the tree.
- `latlng_to_cell(lat, lng, res)` returns the cell containing a point, and `cell_to_latlng(cell)` returns a cell's center.
- `cell_to_parent(cell, res)` returns the cell's ancestor at `res`, found by ID (the cell itself at its own resolution).
- `cell_to_boundary(cell)` returns the cell's own polygon, G(c), as a shapely `Polygon` in lng/lat.
- `footprint(cell, res)` returns the area covered by the cell's descendants at `res`, F_r(c), as a shapely geometry.
- `avg_cell_area_km2(res)`, `MAX_RES`, and `grid` (the `parent`/`children`/`resolution` triple the core algorithms use).

Set design works the same way in every system:

```python
from dggs_sets import h3

# weights: cell -> value of including it, here 20 - drive minutes (0 if unreachable)
bag = h3.design(weights, lam=1.0, size='cocompact')   # or 'compact', 'cells'
bags = [h3.design(weights, lam) for lam in (0.1, 1, 10)]   # a sweep
zone = h3.uncompact(bag, 10)                          # the chosen cells
```

## Layout

The algorithms are plain Python, and they're built on one internal primitive. `core.tree.cell_tree(grid, cells)` returns the tree above the cells as a list of (parent, children) pairs, finest first, so children always come before their parent. A `Grid` is just three functions: `parent`, `children` and `resolution`.

Every algorithm that walks up the tree is a single loop, `for p, kids in cell_tree(grid, cells):`, that combines the children's answers:

- `compact(grid, cells)`: are all the children full?
- `cocompact(grid, cells)`: which is the cheaper bag, as is or flipped?
- `design(grid, weights, lam, size)`: which has the better value? This is the same structure, with weights.

The per-DGGS modules (`h3.compact(cells)` and so on) fill in their grid.

| file | what |
|---|---|
| `src/dggs_sets/{h3,s2,a5}.py` | per-DGGS adapters: a `Grid`, polygon fill, and the algorithms bound to it; the interface |
| `src/dggs_sets/core/tree.py` | `Grid`, `cell_tree`, `descendants`, `cell_to_parent` |
| `src/dggs_sets/core/compaction.py` | `compact(grid, cells)`, `cocompact(grid, cells)`, `uncompact`, `contains` |
| `src/dggs_sets/core/design.py` | `design(grid, weights, lam, size)`: the three set-design solvers |
| `src/dggs_sets/data/` | `states()`, `ct_counties()`, `cellsets(m, geoms, res)`, `nyc_field('h3' or 's2')`; the boundaries are fetched and cached on first use, sources in its README |
| `src/dggs_sets/plot.py` | drawing helpers: cells, footprints and bags, and `save` (palette PNG) |
| `scripts/` | the talk's figure and analysis scripts, built on the package |
| `talk/` | the Quarto deck |
| `tests/` | brute-force checks, cross-checks against native libraries, and the slide code |

The street network and routing behind the travel times aren't needed here: `design` only needs a weight per cell.

## Bags

A bag is a multiset of cells, possibly mixing resolutions and possibly nested. A fine cell belongs to the set a bag describes when an **odd** number of its ancestors, itself included, appear in the bag. Placing a child next to its parent therefore cuts that child out of the parent. A cell may appear more than once; two copies cancel, so duplicates are never useful, but they're legal and the logic is unchanged. The simplest way to see co-compaction is "uncompact everything into the bag, then cancel out pairs"; `cocompact` finds the smallest bag, which has no duplicates.

Any collection of cells is a valid bag. That isn't true of signed `{cell: ±1}` encodings, where a single negative cell on its own is already invalid. A standard compacted set is just a bag with no nesting.

`cocompact` makes one pass up the tree. At each node it keeps the cheaper of two options:

1. build the node up from its children;
2. take the node itself and toggle out the parts that aren't wanted.

The result is exactly minimal, which the tests confirm by brute force on a toy quadtree. The algorithm only needs `parent`, `children` and `resolution`, so H3 pentagons and A5's 5-child base cells need no special handling (`src/dggs_sets/core/compaction.py`).

## Backends

| system | package | cell ids | children | polygon fill |
|---|---|---|---|---|
| H3 | `h3` (`basic_int` API) | int | 7 (6 for pentagons) | native `geo_to_cells` |
| S2 | `s2geometry` (official bindings) | int | 4 | fixed-level `S2RegionCoverer`: interior cells kept as is, boundary cells kept if their centers are in the polygon |
| A5 | `pya5` | int | 5 at res 0, then 4 | native `polygon_to_cells` (center containment), one polygon at a time |

Polygon edges are geodesics in S2 but straight lines in longitude/latitude in H3. Because US state boundaries are densely sampled, the difference is negligible. Each system's center fill matches Colorado's area to within 1%.

## Results: US states

Run `uv run scripts/stats.py` (about 25 s). Each system uses one resolution for every state, chosen so average cell areas are close. The totals go to stdout and per-state rows are written to `scripts/out/stats.csv`.

Each state is compacted and co-compacted on its own, then the counts are summed over all states. Compact and cocompact sizes are shown as a percentage of the total cell count, and the last column is how many times smaller the co-compacted set is than the compacted one:

| system | res | avg km² | cells | compact (% of cells) | co-compact (% of cells) | co-compact smaller by |
|---|---|---|---|---|---|---|
| H3 | 7 | 5.16 | 1,786,083 | 4.80% | 2.85% | 1.69× |
| S2 | 12 | 5.07 | 2,028,107 | 3.38% | 2.29% | 1.48× |
| A5 | 11 | 8.11 | 1,154,010 | 5.20% | 3.21% | 1.62× |

A5 has aperture 4, so it has no resolution near 5 km². Res 11 is the closest in log terms. The smallest states get few cells at these resolutions: DC has 34 H3 cells, so its row is noisy.

The H3 cell, `compact` and `cocompact` counts match h3coco 0.2.0's signed `{cell: ±1}` co-compaction on every state, as expected: how cells are represented doesn't affect the count. (Checked once by hand; it isn't part of the tests.) A bag and a signed dict carry the same information: a token's sign is + when an even number of its strict ancestors are also tokens, and − when the number is odd.

## Geometric cells and footprints

Compaction happens entirely in cell IDs, so a compacted cell means "this set of fine cells", whatever its own polygon looks like. Two shapes therefore belong to a cell c at resolution k, viewed from a working resolution r ≥ k:

- D_r(c) is the set of c's descendants at resolution r. It is defined purely by the IDs, through parent and children.
- G(c) is the **geometric cell**: c's own polygon, from `cell_to_boundary`.
- F_r(c) = ⋃ { G(d) : d ∈ D_r(c) } is c's **footprint**: the area its descendants actually cover, from `footprint`.

The footprint is what c stands for. The same idea extends to sets:

- A compacted set S covers ⋃ { F_r(c) : c ∈ S }.
- A co-compacted bag B covers ⊕ { F_r(c) : c ∈ B }, the XOR of its footprints: a point is inside when an odd number of footprints cover it.
- Drawing ⋃ G(c) instead is the geometric reading. Its gaps and overlaps are exactly the places where G(c) and F_r(c) differ.

How far apart G and F are depends on the system. `uv run scripts/footprints.py` (about 17 s) compares them for 100 random cells per system, sampled between 60°S and 60°N and away from the antimeridian. IoU is area(G ∩ F) / area(G ∪ F). Mismatch is area(G Δ F) / area(G), the share of the cell's area that the geometric reading gets wrong:

| system | res | footprint depth | mean IoU | mean mismatch | mismatch range |
|---|---|---|---|---|---|
| S2 | 10 | 1, 2, 5 | 1.000 | 0% | 0% |
| H3 | 5 | 1 | 0.867 | 14.3% | 14.3% (constant) |
| H3 | 5 | 2 | 0.885 | 12.2% | 12.2–12.3% |
| H3 | 5 | 4 | 0.878 | 13.0% | 13.0% (constant) |
| A5 | 9 | 1 | 0.458 | 74.7% | 64–84% |
| A5 | 9 | 2 | 0.471 | 72.5% | 59–84% |
| A5 | 9 | 5 | 0.479 | 71.1% | 56–84% |

- **S2: the same.** Children exactly tile their parent, so F_r(c) = G(c).
- **H3: approximate.** The footprint is the hexagon with a crinkly edge, which converges to the Gosper island. 12–14% of the area differs, and it is the same for every cell (exactly 1/7 one level down).
- **A5: different shapes.** A5's hierarchy lives on a triangular lattice: each dodecahedron face is split into 5 triangles, and each resolution splits every triangle into 4. The pentagon is only how a cell is drawn at its own resolution, so F_r(c) converges to a triangle or a rhombus (two triangles back to back), depending on the cell: over Connecticut at res 8, 15 of 27 cells give a triangle and 12 a rhombus. Either way it overlaps G(c) by less than half.

## Plots: Connecticut counties

`uv run scripts/plot_ct.py` takes about 8 s. First it draws the whole state in coarse cells, one figure per system and level (`ct_state_{h3,s2,a5}_*.png`: H3 res 7, S2 level 12, A5 res 11, cells of about 5 km², 1,600–3,100 for the state, and one level coarser), for the slides that introduce the three cell shapes. Then it fills each county at resolution r (H3 8, S2 14, A5 13), compacts it, and draws three steps to `talk/figs/`:

1. `ct_*_geo_*.png`: the compacted cells, drawn as geometric cells G(c). In H3 and A5, coarse cells gap and overlap with their finer neighbors.
2. `ct_*_footprint_*.png`: the compacted cells, drawn as footprints F_r(c). These tile exactly.
3. `ct_*_fine_*.png`: the filled cells at r, covering the same area as the footprints. `ct_counties_h3_7.png` (from `named()`) is the counties at res 7 with their names on, for the slide that introduces them.

S2 skips step 2, because there G(c) = F_r(c).

## Plots: co-compacted bags

`uv run scripts/plot_cocompact.py` takes about 4 s. It draws each fine cell one of two ways:

- green: the fine cell is in, because an odd number of tokens cover it.
- hatched: the fine cell is carved out, because an even number of tokens cover it.

Each token is outlined by its footprint. The bag is built up by nesting depth, not by resolution:

1. Add the top-level tokens, whatever their resolution.
2. Take away the tokens nested inside those.
3. Add back the next layer, and so on.

That way each step only adds or only takes away. Each step draws the set decoded from the tokens added so far. That step's tokens are outlined in black and earlier ones in grey. The last step, `all`, outlines every token the same way. XOR doesn't depend on order, so the result is the same as the query's walk up the ancestors by resolution. The script writes to `talk/figs/coco_*.png`:

- `coco_stuck_*`: the co-compaction pitch. One H3 cell with all of its grandchildren but one: 48 cells, 12 compacted, and 2 as a bag.
- `coco_ggc_*`: the deck's version, one level deeper: a res-5 cell with all of its res-8 great-grandchildren but one: 342 cells, 18 compacted, and 2 as a bag.
- `coco_phantom_*`: one H3 res-5 cell P, with three of its children as tokens: two neighbors and the center child. Together their outlines trace the full outline of a fourth child that isn't a token. Counting loops would call that child carved out. Counting its ancestors in the bag, which is just P, correctly says it's in. To read a bag, follow the IDs, not the picture.
- `coco_ct_{h3,s2}_{r}_*`: Connecticut's state outline, four steps each:
  - H3 r = 7: 124 + 64 + 17 + 5 = 210 cells in the bag, versus 318 compacted.
  - S2 r = 12: 87 + 106 + 17 + 1 = 211 cells in the bag, versus 318 compacted.

  Every step is easy to see at these resolutions; step 4 is a second take-away.

## Set design: a NYC isochrone

<!-- The numbers here and on the slides are copied from plot_design.py's printed output; update them together after a rerun. -->

`uv run scripts/plot_design.py` (about 35 s; it fetches basemap tiles, so it needs a network connection) runs `design` on the 20-minute driving isochrone from downtown Brooklyn. The data is H3 res-10 travel times (`data.nyc_field('h3')`). The value of a cell is v(c) = 20 − minutes (`weights` in the code), and unreachable cells (water, parks) get 0, so they're free. The isochrone has the most fidelity any zone can have, and the λ = 0 answer differs from it only by free cells; every other zone keeps a share of that fidelity, and that share is what the figures report.

| % fidelity | compacted | co-compacted | gain |
|---|---|---|---|
| isochrone (100%) | 3,491 | 2,037 | — |
| 100% (using free cells) | 1,780 | 1,058 | 1.9× |
| ≥ 99.7% | 831 | 575 | 3.5× |
| ≥ 99% | 420 | 288 | 7.1× |
| ≥ 98% | 227 | 126 | 16× |

The exact isochrone is 8,825 cells, 3,491 compacted, or 2,037 as a bag. Optimization does most of the work, and co-compaction adds another 1.4–1.8× on top. That splits about evenly into two parts:

- **The encoding.** Co-compacting a compaction-aware zone after the fact gets about 1.15–1.4×, much less than the 1.71× on the exact isochrone. The optimizer has already used up most of the "almost full" groups.
- **Awareness.** Optimizing with co-compaction in the objective gets about another 1.1–1.5×.

The frontier shows this as a dashed line.

The same example runs in S2 at level 16, from `data.nyc_field('s2')`, and its figures are named `design_s2_*` in the same pattern. Exactly, the isochrone is 8,006 cells, 2,549 compacted, or 1,604 as a bag. Keeping 99% of the fidelity, the zone is 302 compacted cells or 224 as a bag, 7.2× smaller than the co-compacted isochrone. The numbers are close to H3's.

The script writes three kinds of map:

- `talk/figs/design_field.png`: the field alone, which the slides explain first;
- `design_exact.png`: the isochrone, labeled like the field; `design_iso.png`: the same, labeled like the movie frames;
- `design_{0..17}.png`: the λ movie, 18 penalties from 0.001 to 2000.

Each map shows:

- every cell colored by minutes − 20, on a diverging scale: blue inside the limit, white at 20 minutes, red past it;
- unreachable cells in grey;
- the compacted cells outlined in black;
- the zone's edge in neon green;
- all of it over a light-grey Esri basemap, credited on each figure.

It also writes `design_frontier.png`. The co-compacted sizes are only printed: their pictures show nothing the compacted ones don't.

The **universe** is a box around the isochrone, longitude −74.15 to −73.74 and latitude 40.56 to 40.84, cut from the five-borough field: 71,209 cells. Every res-10 cell in it is either reached (it has a drive time) or verified unreachable (water, or roads with no path), and unreachable cells are free. Cells outside the box were never computed, so their drive time is unknown: they're absent from `weights` and `design` never chooses them. The maps draw the whole universe, so it shows as a rectangle. Cropping from the full field to this box changes none of the numbers: no optimal zone reaches past it. `tests/test_design.py` checks `design` against brute force on a 16-leaf quadtree.

## Slides

The talk is a single Quarto reveal.js deck. `talk/index.qmd` is the markdown source and `talk/style.css` the house style. To build it:

```
just slides      # quarto render talk/index.qmd (writes the gitignored talk/index.html), then open it
just preview     # rebuild on every edit
```

The `justfile` holds the other repeated operations too (`just` lists them): `test`, `stats`, `figs` and `design` to regenerate figures, and `checks` for the footprint and query-error numbers.

Every figure goes through `dggs_sets.plot.save`, which writes a palette PNG: 64 colors for the flat-color figures and 256 for the λ movie, with its basemap and colormap. They look the same as RGBA and are 4–6× smaller, which keeps the deck light enough to host.

Every slide is a `##` heading followed by markdown. There are five layouts:

| layout | markdown |
|---|---|
| title + bullets | `## Title`, then a list |
| title + code beside bullets | `## Title`, then `:::: {.columns}` holding a `::: {.column .code}` (sized to the code) and a `::: {.column}` (takes the rest) |
| title + image | `## Title`, then `![](figs/x.png){.r-stretch}` to fill the rest of the slide |
| image only | `## {background-image="figs/x.png" background-size="contain"}`, optionally with `::: {.note}` for text in the bottom-right corner |
| interlude | `## {.interlude}`, then one line of text: big and centered |

The deck has no speaker notes. Press <kbd>s</kbd> for the speaker view, which has a timer. A placeholder, if one is needed, reads `[TODO: ...]{.todo}` and shows in red italics. Part title slides use a level-2 heading with the `.part` class. A level-1 `#` heading would make reveal.js stack that part's slides vertically, and the right arrow would skip them.

The title sits in the upper left, and there are no slide numbers. Code blocks sit in light grey boxes. To highlight lines, use `code-line-numbers`: for example, ```` ```{.python code-line-numbers="3,9"} ```` marks lines 3 and 9 in yellow.

The deck holds both talks, so it works for an hour-long run-through. At FOSS4G they're two separate 20-minute talks. The deck runs: overall title, About me, Part 1, Part 2 (each part opens with a `## Part N {.part}` slide).

- **Part 1:** *Hierarchical (Co-)Compaction for DGGS Cells*
- **Part 2:** *DGGS Set Design: Compaction-Aware Optimization*. It's built around the NYC isochrone: the exact isochrone, the objective Σ v(c) − λ‖S‖ with three choices of size, then the finale: the λ movie, the fidelity-vs-size frontier, and the numbers.

Part 1, with rough timings:

1. **Opening** (about 1 min). About me, DGGSs and polygons to cells, with Connecticut in each system at one resolution.
2. **Cellsets** (about 2 min). A cellset is a set of cells at one resolution, how the talk represents a region; then many named cellsets, with Connecticut's counties as the picture, then the question: which cellsets contain this point? The flat query answers it by checking every cellset, a set comprehension; then the other way, a reverse index (cell → cellsets) built once, so a query is one lookup with no loop over the cellsets. Then the motivation: 17k cells for the counties, 12.5M for the US states at H3 res 8.
3. **Compaction** (about 3.5 min). The hierarchy as one H3 cell, then its children, grandchildren and great-grandchildren (7x, then 343x three levels down), with the convention that "children at res r" means descendants. Compaction as the walk up the tree, California's numbers (521k → 7.2k), then Connecticut's counties uncompacted and compacted.
4. **Gaps, and the logical reading** (about 3 min). "What's going on with those gaps?": a point inside the counties but in no compacted cell's polygon. The fix: a compacted cell means its footprint (the Gosper island in H3), which is identical to the uncompacted coverage. Then the query on compacted cellsets: `compact`, the same `reverse_index`, walk up the ancestors with union.
5. **S2 and A5** (about 2.5 min). S2's children nest, so one picture shows four levels; A5's don't, and the footprint drifts to a triangle or a rhombus. The compacted counties as footprints in all three systems.
6. **Co-compaction** (about 5.5 min). All of a cell's great-grandchildren but one: 342 cells, 18 compacted, 2 in a bag. Bags as multisets read by parity; a 43-cell example as a set, compacted (7) and a bag (3), with its three nesting steps; the Connecticut build-ups (H3 r = 7, S2 r = 12). The bag query is the compacted query with `^=` for `|=`, shown side by side.
7. **Computing the smallest bag** (about 1.5 min). The sketch: walk up, two bags per cell (positive and negative), a parent combines positives or joins the bag and combines negatives, keep the smaller. Dynamic programming on trees; exact.
8. **Benchmark** (about 1 min). The US states: compacted and co-compacted as shares of the cells, and the co-compaction gain. Then questions, with the handoff to Part 2: given a set versus designing one.

`tests/test_query_slides.py` runs every code block marked `check="name"` and compares its query against brute-force membership in all three systems, using the US states plus an overlapping "New England" cellset.

Four more scripts:

- `scripts/query_errors.py` (about 20 s) samples 100k random points in a contiguous-US box. Of the roughly 59k that land in a state, the geometric query is wrong for 0% in S2, 2.7% in H3 and 13.9% in A5.
- `scripts/plot_query.py` draws one H3 cell over its footprint, the geometric-vs-logical query figure (no longer in the deck); it also fixes the cell the hierarchy figures use.
- `scripts/plot_hierarchy.py` draws the same H3 cell, then its seven children with the parent's outline dashed, for the hierarchy slides.
- `scripts/plot_encoder.py` draws the encoder example (no longer in the deck), one S2 cell drawn as a square: 39 of its 64 descendants, 27 compacted, 18 tokens.

## Development

```
uv run pytest    # about 10 s
```

## License

- Code: [MIT](LICENSE).
- Slides, text and figures (`talk/`): [CC BY 4.0](talk/LICENSE), except that the isochrone maps include Esri basemap tiles under Esri's terms, and the isochrone figures carry the OpenStreetMap notice below.
- Data: the US states are from the Census Bureau (public domain); Connecticut's counties are from CT DEEP (CC0). The NYC drive-time fields were computed from OpenStreetMap data and are © OpenStreetMap contributors, under the [ODbL](https://opendatacommons.org/licenses/odbl/). See [AGENTS.md](AGENTS.md) for the reasoning.
