_banned_attrs_dict = [
    '__setitem__',
    '__setattr__',
    'pop',
    'popitem',
    'update',
    'clear',
    'setdefault',
]


def _fn():
    pass


_immutable_types = [
    int,
    float,
    str,
    bytes,
    type(None),
    type(lambda: None),
    type(_fn),
]


def immutalize(value):
    if isinstance(value, dict):
        return Dict(value)
    elif isinstance(value, (list, tuple)):
        return tuple(immutalize(x) for x in value)
    elif isinstance(value, set):
        return frozenset(immutalize(x) for x in value)
    elif type(value) in _immutable_types:
        return value
    raise ValueError('type "{}" is not immutalizable'.format(type(value)))


class Dict(dict):
    def __init__(self, *a, **kw):
        dict.__init__(self, *a, **kw)
        for k, v in self.items():
            dict.__setitem__(self, k, immutalize(v))

    def __setitem__(self, *a):
        raise ValueError('this dict is read-only')
