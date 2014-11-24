from __future__ import absolute_import, print_function
import s


def new(scope, *names):
    return {name: scope[name]
            for name in names}


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


def merge(a, b, concat=False):
    return {k: _merge(k, a, b, concat)
            for k in set(list(a.keys()) +
                         list(b.keys()))}


def _merge(k, a, b, concat):
    a, b, = s.data.freeze(a), s.data.freeze(b)
    assert k in a or k in b, '{k} not in {a} or {b}'.format(**locals())
    if k in a and k in b:
        if isinstance(a[k], dict) and isinstance(b[k], dict):
            return merge(a[k], b[k], concat)
        elif _concatable(a[k], b[k]):
            return a[k] + b[k]
        else:
            return b[k]
    else:
        if k in a:
            return a[k]
        else:
            return b[k]


def take(x, *ks, **kw):
    val = {k: x[k]
           for k in x
           if k in ks}
    if 'padded' in kw:
        val = merge({k: kw['padded'] for k in ks}, val)
    return val


def drop(x, *ks):
    return {k: v
            for k, v in x.items()
            if k not in ks}


def _ks(ks):
    if isinstance(ks, list):
        return tuple(ks)
    elif isinstance(ks, tuple):
        return ks
    raise TypeError('ks must be a list of keys')


def _concatable(*xs):
    return (all(isinstance(x, tuple) for x in xs) or
            all(isinstance(x, list) for x in xs))


def map(mapping_fn, obj):
    def mapper(*x):
        assert isinstance(x, tuple) and len(x) == 2, 'your mapping_fn must take an (<object>, <object>) {}'.format(x)
        val = mapping_fn(*x)
        assert isinstance(val, (list, tuple)) and len(val) == 2, 'your mapping_fn must return an (<object>, <object>) {}'.format(val)
        return val
    fn = lambda x: isinstance(x, tuple) and len(x) == 2 and mapper(*x) or x
    return s.seqs.walk(obj, fn)
