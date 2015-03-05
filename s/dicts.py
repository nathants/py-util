from __future__ import absolute_import, print_function
import s
import collections


def new(scope, *names):
    return {name: scope[name]
            for name in names}


def get(x, ks):
    ks = _ks(ks)
    x = x[ks[0]]
    for k in ks[1:]:
        x = x[k]
    return x


def set(x, ks, v):
    ks = _ks(ks)
    val = {ks[-1]: v}
    for k in reversed(ks[:-1]):
        val = {k: val}
    return merge(x, val)


def merge(a, b, concat=False, freeze=True):
    return {k: _merge(k, a, b, concat, freeze)
            for k in {x for x in list(a.keys()) + list(b.keys())}}


def _merge(k, a, b, concat, freeze):
    if freeze:
        a, b, = s.data.freeze(a), s.data.freeze(b)
    assert k in a or k in b, '{k} not in {a} or {b}'.format(**locals())
    if k in a and k in b:
        if isinstance(a[k], dict) and isinstance(b[k], dict):
            return merge(a[k], b[k], concat, freeze)
        elif concat and _concatable(a[k], b[k]):
            return a[k] + b[k]
        else:
            return b[k]
    else:
        if k in a:
            return a[k]
        else:
            return b[k]


def take(x, ks, **kw):
    ks = _ks(ks)
    val = {k: x[k]
           for k in x
           if k in ks}
    if 'padded' in kw:
        val = merge({k: kw['padded'] for k in ks}, val)
    return val


def drop(x, ks):
    ks = _ks(ks)
    return {k: v
            for k, v in x.items()
            if k not in ks}


@s.schema.check((':or', object, [object]), _return=[object])
def _ks(ks):
    if isinstance(ks, (list, tuple)):
        return tuple(ks)
    else:
        return (ks,)

    raise TypeError('ks must be a list of keys')


def _concatable(*xs):
    return (all(isinstance(x, tuple) for x in xs) or
            all(isinstance(x, list) for x in xs))


def map(mapping_fn, obj):
    def mapper(*x):
        val = mapping_fn(*x)
        assert isinstance(val, (list, tuple)) and len(val) == 2, 'your mapping_fn must return an (<object>, <object>) {}'.format(val)
        return val
    fn = lambda x: isinstance(x, tuple) and len(x) == 2 and mapper(*x) or x
    return s.seqs.walk(fn, obj)


def tree():
    return collections.defaultdict(tree)


def to_nested(obj):
    data = tree()
    for k, v in obj.items():
        data = set(data, k.split('.'), v)
    return dict(data)


def _no_dots(k, v):
    assert '.' not in k, 'you cannot use . in keys names'
    return [k, v]


def to_dotted(obj):
    if not isinstance(obj, dict):
        return obj
    s.dicts.map(_no_dots, obj)
    while any(isinstance(x, dict) for x in obj.values()):
        for k1, v2 in obj.items():
            if isinstance(v2, dict):
                for k2, v2 in obj.pop(k1).items():
                    obj['{}.{}'.format(k1, k2)] = to_dotted(v2)
    return obj
