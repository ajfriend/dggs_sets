# dggs_sets: project conventions

What this repo is, and the decisions to keep following. For humans and agents alike.

## What this is

`dggs_sets` is the **tutorial package** for the FOSS4G talk *DGGS (Co-)Compaction and Set Design* (`talk/index.qmd`). Everything the slides show, the package does: polygons to cells, compaction, co-compaction (XOR bags), the membership queries, and set design, in H3, S2 and A5 behind one interface.

- People **learn from it**; it is not for production. Readability beats speed: the core algorithms should read like pseudocode that could go on a slide.
- It is **not on PyPI** and won't be. Install from GitHub (`uv add git+https://github.com/ajfriend/dggs_sets`) or clone.
- **Store as little data as possible.** `dggs_sets.data` provides the code to fetch (or generate) what the slides use and caches it per user; sources are pinned so the talk's numbers stay reproducible. The NYC drive-time fields are the one exception, shipped in the package because they can't be regenerated from public data. New data follows the same rule: a loader that pulls it down, not a file in git.
- The package is split by what a reader might care about: `dggs_sets.h3/.s2/.a5` (the interface), `dggs_sets.core` (the algorithms), `dggs_sets.data`, `dggs_sets.plot`. `scripts/` makes the talk's figures and numbers from those; it is not part of the package.
- The slides and the package live in **one repo**, because the tests run the deck's code blocks (`check="name"`) against the package. They can't drift.

## Licensing

Three kinds of content, three licenses. Don't blur them.

- **Code: MIT** (`LICENSE`). Not Creative Commons: CC says itself not to use its licenses for software (no patent language, no source/binary distinction, incompatible with the GPL and most open-source policies). MIT is the "copy a function into your project" license, which is the point of a tutorial.
- **Slides, text and figures: CC BY 4.0** (`talk/LICENSE`).
- **Data: credit the source, honor its license.**
  - US states: Census Bureau cartographic boundaries, public domain.
  - Connecticut counties: credit the source in `src/dggs_sets/data/README.md`.
  - NYC drive-time fields: computed from OpenStreetMap speed limits, so they are a derived database under the **ODbL**. Ship them with "© OpenStreetMap contributors" and share-alike on those files; credit the data as above, nothing more.
  - Figures with basemap tiles carry the tile provider's credit on the figure.
- Adding data or code from elsewhere: note its license in the same commit.

## Terminology

- A **cellset** is a set of cells at one resolution: how the talk represents a region. Say "cellset", not "set of cells", "region" (the geographic thing it approximates) or "family".
- Several named cellsets are just `cellsets`, a dict name → cellset; `data.cellsets(m, geoms, r)` builds one.
- The point/cell query is `containing(cell)`: which cellsets contain this cell. "Membership" is reserved for a cell being in a cellset.
- A co-compacted cellset is a **bag**: a multiset of cells at mixed resolutions, read by parity (XOR). Duplicates are allowed, and they cancel in pairs: not optimal, but legal, and the logic works unchanged. That's the teaching order: "uncompact everything into the bag, then cancel out pairs"; `cocompact` returns the smallest bag, which has no duplicates. Never "signed cells", and in the talk never "tokens": a bag's members are just "cells" or "cells in the bag". (The package code still says `tokens` internally.)

## Working conventions

- `just` holds the repeated operations (`just slides`, `just figs`, `just test`); add new ones there.
- Figures are saved through `dggs_sets.plot.save` (palette PNG). Match its style: green fill, black edges, one color.
- Slides: no `::: notes` blocks, anywhere; the author keeps talking points elsewhere. Image flip sequences are one beat, not N slides.
- Python: `uv` only, no `python -c`, PEP 723 for scripts, no argparse, single quotes.
- Git: commit only when asked. The repo is public at github.com/ajfriend/dggs_sets; a push to main publishes the deck.
