# Repeated operations. `just` alone lists them.

[private]
default:
    @just --list --unsorted

# Build the deck and open it in the browser
slides: render
    open talk/index.html

# Build the deck: talk/index.qmd -> talk/index.html
render:
    quarto render talk/index.qmd

# Rebuild the deck on every edit and keep the browser in sync
preview:
    quarto preview talk/index.qmd

# Run the tests
test:
    uv run pytest

# Compression statistics on US states, across H3, S2 and A5
stats:
    uv run scripts/stats.py

# Regenerate every figure the deck uses (talk/figs)
figs:
    uv run scripts/plot_ct.py
    uv run scripts/plot_hierarchy.py
    uv run scripts/plot_cocompact.py
    uv run scripts/plot_encoder.py
    uv run scripts/plot_query.py
    uv run scripts/plot_design.py

# The Part 2 isochrone figures only: the movie and the frontier
design:
    uv run scripts/plot_design.py

# The two appendix checks: footprint vs cell distances, and query error rates
checks:
    uv run scripts/footprints.py
    uv run scripts/query_errors.py

# Remove the rendered deck
clean:
    rm -rf talk/index.html talk/index_files talk/.quarto
