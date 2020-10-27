import collections
import util.iter

def new(scope, *names):
    return {name: scope[name]
            for name in names}

def get(x, ks):
    ks = _ks(ks)
    x = x.get(ks[0], {})
    for k in ks[1:]:
        x = x.get(k, {})
    return x

def set(x, ks, v):
    ks = _ks(ks)
    val = {ks[-1]: v}
    for k in reversed(ks[:-1]):
        val = {k: val}
    return merge(drop_in(x, ks), val)

def merge(a, b, concat=False):
    return {k: _merge(k, a, b, concat)
            for k in {x for x in list(a) + list(b)}}

def _merge(k, a, b, concat):
    assert k in a or k in b, '{k} not in {a} or {b}'.format(**locals())
    if k in a and k in b:
        if isinstance(a[k], dict) and isinstance(b[k], dict):
            return merge(a[k], b[k], concat)
        elif concat and _concatable(a[k], b[k]):
            return a[k] + b[k]
        else:
            return b[k]
    else:
        if k in a:
            return a[k]
        else:
            return b[k]

def update_in(x, ks, fn, *a, **kw):
    return set(x, ks, fn(get(x, ks), *a, **kw))

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

def drop_in(x, ks):
    if len(ks) == 1:
        return drop(x, ks)
    elif get(x, ks[:-1]):
        return update_in(x, ks[:-1], lambda y: drop(y, ks[-1]))
    else:
        return x

def _ks(ks):
    if isinstance(ks, (list, tuple)):
        return tuple(ks)
    else:
        return (ks,)
    raise TypeError('ks must be a list of keys')

def _concatable(*xs):
    return all(isinstance(x, tuple) for x in xs) or all(isinstance(x, list) for x in xs)

def map(mapping_fn, obj):
    def mapper(k, v):
        val = mapping_fn(k, v)
        assert isinstance(val, (list, tuple)) and len(val) == 2, 'your mapping_fn must return an (<object>, <object>) {}'.format(val)
        return val
    fn = lambda x: isinstance(x, tuple) and len(x) == 2 and mapper(*x) or x
    return util.iter.walk(fn, obj)

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
    map(_no_dots, obj)
    while any(isinstance(x, dict) for x in obj.values()):
        for k1, v2 in list(obj.items()):
            if isinstance(v2, dict):
                for k2, v2 in obj.pop(k1).items():
                    obj['{}.{}'.format(k1, k2)] = to_dotted(v2)
    return obj
