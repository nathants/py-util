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
with s.exceptions.ignore():
    _json_types += (unicode,) # noqa


def jsonify(value):
    if isinstance(value, dict):
        return {jsonify(k): jsonify(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple, set)):
        return [jsonify(x) for x in value]
    elif isinstance(value, bytes):
        return value.decode('utf-8')
    elif isinstance(value, _json_types):
        return value
    else:
        value = str(value)
        if ' at 0x' in value:
            value = value.split()[0].split('.')[-1]
        return '<{}>'.format(value.strip('<>'))


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


string_types = (str,
                bytes,)
with s.exceptions.ignore():
    string_types += (unicode,) # noqa


immutable_types = (
    int,
    float,
    type(None),
    types.LambdaType,
    types.FunctionType,
    types.GeneratorType,
    _ImmutableDict,
    _ImmutableSeq,
    _ImmutableSet,
) + string_types


listy_types = (list,
               tuple,
               types.GeneratorType)


with s.exceptions.ignore():
    listy_types += (type({}.items()),
                    type({}.keys()),
                    type({}.values()))


def freeze(value):
    if isinstance(value, immutable_types):
        return value
    elif isinstance(value, dict):
        for k in value.keys():
            assert isinstance(k, s.data.string_types), 'dict keys must be str: {}, {}'.format(k, value)
        return _ImmutableDict({freeze(k): freeze(v) for k, v in value.items()})
    elif isinstance(value, listy_types):
        return _ImmutableSeq(freeze(x) for x in value)
    elif isinstance(value, set):
        return _ImmutableSet(freeze(x) for x in value)
    raise ValueError('{} ({}) not immutalizable'.format(value, type(value)))
