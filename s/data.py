import s


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


with s.exceptions.ignore():
    _immutable_types += [
        basestring,
    ]

_listy_types = [
    list,
    tuple,
]

with s.exceptions.ignore():
    _listy_types += [
        type({}.items()),
        type({}.keys()),
        type({}.values()),
    ]

def immutalize(value):
    if isinstance(value, dict):
        return Dict(value)
    elif isinstance(value, tuple(_listy_types)):
        return tuple(immutalize(x) for x in value)
    elif isinstance(value, set):
        return frozenset(immutalize(x) for x in value)
    elif isinstance(value, tuple(_immutable_types)):
        return value
    raise ValueError('type "{}" is not immutalizable'.format(type(value).__name__))


class Dict(dict):
    def __init__(self, *a, **kw):
        dict.__init__(self, *a, **kw)
        for k, v in self.items():
            dict.__setitem__(self, k, immutalize(v))

    def __setitem__(self, *a):
        raise ValueError('this dict is read-only')
