'''Shared pieces of the per-DGGS modules.'''
import inspect
from functools import partial

import shapely

from .core.tree import cell_tree, descendants

EARTH_AREA_KM2 = 510_065_621.7


def bind(f, *args):
    '''`f` with its leading arguments (the grid, ...) filled in, keeping its name and docstring.'''
    return _named(partial(f, *args), f)


def bind_tree(f, grid):
    '''`f(tree, cells, ...)` as `f(cells, ...)`: builds the tree above `cells`, then walks it.'''
    def g(cells, *args, **kw):
        return f(cell_tree(grid, cells), cells, *args, **kw)
    sig = inspect.signature(f)   # f's own arguments, minus the tree
    g.__signature__ = sig.replace(parameters=list(sig.parameters.values())[1:])
    return _named(g, f)


def _named(g, f):
    '''Give `g` the name and docstring of `f`. Unlike functools.wraps, `help()` and
    `inspect.signature` then show `g`'s own arguments, not `f`'s.'''
    g.__name__, g.__qualname__, g.__doc__, g.__module__ = f.__name__, f.__qualname__, f.__doc__, f.__module__
    return g


def footprint(grid, cell_to_boundary, cell, res):
    '''The area covered by `cell`'s descendants at `res`, as a shapely geometry.

    Vertices are snapped so adjacent descendants' shared edges cancel.
    '''
    cells = descendants(grid, cell, res)
    return shapely.set_precision(shapely.union_all([cell_to_boundary(d) for d in cells]), 1e-9)


def polygons(geo):
    '''Yield each polygon of a Polygon/MultiPolygon __geo_interface__ as a list of rings.'''
    geo = getattr(geo, '__geo_interface__', geo)
    if geo['type'] == 'Polygon':
        yield geo['coordinates']
    elif geo['type'] == 'MultiPolygon':
        yield from geo['coordinates']
    else:
        raise ValueError(f'unsupported geometry type: {geo["type"]}')
