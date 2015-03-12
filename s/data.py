from __future__ import absolute_import
import six
import s
import types
import binascii


json_types = (list,
              str,
              dict,
              int,
              float,
              tuple,
              bool,
              type(None))
with s.exceptions.ignore():
    json_types += (unicode,) # noqa


def jsonify(value):
    if isinstance(value, dict):
        return {jsonify(k): jsonify(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple, set)):
        return [jsonify(x) for x in value]
    elif isinstance(value, bytes):
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            return b2a(value)
    elif isinstance(value, json_types):
        return value
    else:
        if hasattr(value, '_action'):
            action = '={}'.format(value._action)
        else:
            action = ''
        value = str(value)
        if ' at 0x' in value:
            value = value.split()[0].split('.')[-1]
        return '<{}{}>'.format(value.strip('<>'), action)


def a2b(x):
    return binascii.a2b_base64(x.split('<b2a_base64=')[-1][:-1])


def b2a(x):
    return '<b2a_base64={}>'.format(binascii.b2a_base64(x).decode('utf-8').strip())


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


class _ImmutableTuple(tuple):
    pass


_banned_attrs_list = [
    '__add__',
    '__iadd__',
    'append',
    'clear',
    'extend',
    'insert',
    'pop',
    'remove',
    'reverse',
    'sort',
]


class _ImmutableList(list):
    def _raise_error(self, *a, **kw):
        raise ValueError('this list is read-only')

    for k in _banned_attrs_list:
        locals()[k] = _raise_error



class _ImmutableSet(frozenset):
    pass


string_types = (str,)
with s.exceptions.ignore():
    string_types += (unicode,) # noqa


immutable_types = (
    bytes,
    int,
    float,
    type(None),
    types.LambdaType,
    types.FunctionType,
    types.GeneratorType,
    _ImmutableDict,
    _ImmutableTuple,
    _ImmutableList,
    _ImmutableSet,
) + string_types
with s.exceptions.ignore():
    import bson.objectid
    immutable_types += (bson.objectid.ObjectId,)

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
        return _ImmutableDict({freeze(k): freeze(v) for k, v in value.items()})
    elif isinstance(value, tuple):
        return _ImmutableTuple(freeze(x) for x in value)
    elif isinstance(value, list):
        return _ImmutableList(freeze(x) for x in value)
    elif isinstance(value, set):
        return _ImmutableSet(freeze(x) for x in value)
    raise ValueError('not immutalizable: {} <{}>'.format(value, type(value)))
