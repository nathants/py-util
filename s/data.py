from __future__ import absolute_import
import s
import types


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


_immutable_types = (
    int,
    float,
    str,
    bytes,
    type(None),
    type(lambda: None),
    type(_fn),
)


with s.exceptions.ignore():
    _immutable_types += (basestring,)


_listy_types = (list,
                tuple)


with s.exceptions.ignore():
    _listy_types += (type({}.items()),
                     type({}.keys()),
                     type({}.values()))


def immutalize(val):
    if isinstance(val, types.GeneratorType):
        val = tuple(val)

    if hasattr(val, '_immutalized'):
        return val
    with s.exceptions.ignore():
        val._immutalized = True

    if isinstance(val, _immutable_types):
        return val
    elif isinstance(val, dict):
        return _ImmutableDict({k: immutalize(v) for k, v in val.items()})
    elif isinstance(val, _listy_types):
        return tuple(immutalize(x) for x in val)
    elif isinstance(val, set):
        return frozenset(immutalize(x) for x in val)

    raise ValueError('type "{}" is not immutalizable'.format(type(val).__name__))


class _ImmutableDict(dict):
    def __setitem__(self, *a):
        raise ValueError('this dict is read-only')
