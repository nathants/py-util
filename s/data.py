from __future__ import absolute_import, print_function
import types


disabled = False


json_types = (
    list,
    str,
    dict,
    int,
    float,
    tuple,
    bool,
    type(None),
)


try:
    json_types += (unicode,) # noqa
except:
    pass


string_types = (str,)


try:
    string_types += (unicode,) # noqa
except:
    pass


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


def freeze(value, data_only=False):
    if disabled or isinstance(value, immutable_types):
        return value
    elif hasattr(value, 'add_done_callback'):
        future = type(value)()
        @value.add_done_callback
        def fn(f):
            try:
                future.set_result(freeze(f.result(), data_only))
            except Exception as e:
                future.set_exception(e)
        return future
    elif isinstance(value, dict):
        return _ImmutableDict({freeze(k, data_only): freeze(v, data_only)
                               for k, v in value.items()})
    elif isinstance(value, tuple):
        return _ImmutableTuple(freeze(x, data_only) for x in value)
    elif isinstance(value, list):
        return _ImmutableList(freeze(x, data_only) for x in value)
    elif isinstance(value, (set, frozenset)):
        return _ImmutableSet(freeze(x, data_only) for x in value)
    elif data_only:
        return value
    else:
        raise ValueError('not freezable: {} <{}>'.format(value, type(value)))


def thaw(value):
    if disabled:
        return value
    elif isinstance(value, dict):
        return {thaw(k): thaw(v) for k, v in value.items()}
    elif isinstance(value, tuple):
        return tuple(thaw(x) for x in value)
    elif isinstance(value, list):
        return [thaw(x) for x in value]
    elif isinstance(value, (set, frozenset)):
        return {thaw(x) for x in value}
    else:
        return value
