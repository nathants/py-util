from __future__ import absolute_import, print_function
import copy


def get(x, *ks):
    ks = _ks(ks)
    x = x[ks[0]]
    for k in ks[1:]:
        x = x[k]
    return x


def put(x, v, *ks):
    ks = _ks(ks)
    val = {ks[-1]: v}
    for k in reversed(ks[:-1]):
        val = {k: val}
    return merge(x, val)


def merge(a, b, concat=True):
    if not isinstance(a, dict):
        return b
    a = copy.deepcopy(a)
    for bk, bv in b.items():
        if bk in a and isinstance(bv, dict):
            a[bk] = merge(a[bk], bv)
        elif bk in a and _concatable(a[bk], bv) and concat:
            a[bk] += bv
        else:
            a[bk] = bv
    return a


def only(x, *ks, **kw):
    val = {k: x[k] for k in x if k in ks}
    if 'padded' in kw:
         val = merge({k: kw['padded'] for k in ks}, val)
    return val


def drop(x, *ks):
    return {k: v for k, v in x.items() if k not in ks}


def _ks(ks):
    if isinstance(ks, list):
        ks = tuple(ks)
    elif not isinstance(ks, tuple):
        raise TypeError('ks must be a tuple of keys')
    return ks


def _concatable(*xs):
    return {type(x) for x in xs} ^ {list, tuple} in [{list}, {tuple}]
