import collections
import util.iter

def new(scope, *names):
    return {name: scope[name]
            for name in names}

def get(x, ks):
    ks = _ks(ks)
    x = x.get(ks[0], {})
    for k in ks[1:]:
        if isinstance(x, (tuple, list)):
            x = x[int(k)]
        else:
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
    assert k in a or k in b, f'{k} not in {a} or {b}'
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
        assert isinstance(val, (list, tuple)) and len(val) == 2, f'your mapping_fn must return an (k, v): {val}'
        return val
    def fn(x):
        if isinstance(x, dict):
            return dict(mapper(*kv) for kv in x.items())
        else:
            return x
    return util.iter.walk(fn, obj)

def tree():
    return collections.defaultdict(tree)

def _to_lists(v):
    if isinstance(v, dict) and all(k.isdigit() for k in v):
        new_v = [v[k] for k in sorted(v, key=int)]
        if len(new_v) < max(int(k) for k in v):
            raise IndexError
        return new_v
    else:
        return v

def from_dotted(obj):
    data = tree()
    for k, v in obj.items():
        data = set(data, str(k).split('.'), v)
    data = dict(data)
    data = util.iter.walk(_to_lists, data)
    return data

def _validate_keys(x):
    if isinstance(x, dict):
        for k in x:
            assert k.strip(), f'you cannot use blank keys: "{k}"'
            assert ' ' not in k, f'you cannot use spaces in key names: "{k}"'
            assert '.' not in k, f'you cannot use "." in key names: "{k}"'
    return x

def to_dotted(obj):
    util.iter.walk(_validate_keys, obj)
    if not isinstance(obj, (tuple, list, dict)):
        return obj
    if isinstance(obj, (list, tuple)):
        new_obj = {}
        for i, v in enumerate(obj):
            new_obj[str(i)] = v
        obj = new_obj
    obj = obj.copy()
    while any(isinstance(x, (dict, tuple, list)) for x in obj.values()):
        for k1 in list(obj):
            v1 = obj.pop(k1)
            if isinstance(v1, dict):
                for k2, v2 in v1.items():
                    obj[f'{k1}.{k2}'] = to_dotted(v2)
            elif isinstance(v1, (tuple, list)):
                for i, v2 in enumerate(v1):
                    obj[f'{k1}.{i}'] = to_dotted(v2)
            else:
                obj[k1] = v1
    return obj
