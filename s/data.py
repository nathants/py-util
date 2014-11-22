from __future__ import absolute_import
import s
import types

_json_types = (list,
               str,
               dict,
               int,
               float,
               tuple,
               bool,
               type(None))
try:
    _json_types += (unicode,)
except:
    _json_types += (bytes,)


def jsonify(val):
    if isinstance(val, dict):
        return {jsonify(k): jsonify(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple, set)):
        return [jsonify(x) for x in val]
    elif isinstance(val, _json_types):
        return val
    else:
        val = str(val)
        if ' at 0x' in val:
            val = val.split()[0].split('.')[-1]
        return '<{}>'.format(val.strip('<>'))


_banned_attrs_dict = [
    '__setitem__',
    '__setattr__',
    'pop',
    'popitem',
    'update',
    'clear',
    'setdefault',
]


class _ImmutableDict(dict):
    def _raise_error(self, *a, **kw):
        raise ValueError('this dict is read-only')

    for k in _banned_attrs_dict:
        locals()[k] = _raise_error


class _ImmutableSeq(tuple):
    pass


class _ImmutableSet(frozenset):
    pass


_immutable_types = (
    int,
    float,
    str,
    bytes,
    type(None),
    types.LambdaType,
    types.FunctionType,
    types.GeneratorType,
    _ImmutableDict,
    _ImmutableSeq,
    _ImmutableSet,
)


with s.exceptions.ignore():
    _immutable_types += (basestring,)


_listy_types = (list,
                tuple,
                types.GeneratorType)


with s.exceptions.ignore():
    _listy_types += (type({}.items()),
                     type({}.keys()),
                     type({}.values()))


def immutalize(val):
    if isinstance(val, _immutable_types):
        return val
    elif isinstance(val, dict):
        return _ImmutableDict({immutalize(k): immutalize(v) for k, v in val.items()})
    elif isinstance(val, _listy_types):
        return _ImmutableSeq(immutalize(x) for x in val)
    elif isinstance(val, set):
        return _ImmutableSet(immutalize(x) for x in val)
    raise ValueError('{} ({}) not immutalizable'.format(val, type(val)))
