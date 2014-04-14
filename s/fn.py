from __future__ import absolute_import
import contextlib
import logging
import time
import types
import s


trace_funcs = {
    'logic': {
        'in': lambda name, *a, **kw: logging.debug({
            'direction': 'in',
            'name': name,
            'args': a,
            'kwargs': kw,
            'time': time.time(),
            'state': state(),
            'stack': _format_stack(stack()),
        }),
        'out': lambda name, val: logging.debug({
            'direction': 'out',
            'name': name,
            'value': val,
            'time': time.time(),
            'state': state(),
            'stack': _format_stack(stack()),
        })
    }
}


trace_funcs['glue'] = trace_funcs['flow'] = trace_funcs['logic']


def _format_stack(val):
    return [':'.join(map(str, x)) for x in val]


@contextlib.contextmanager
def state_layer(kind, func_name):
    _backup = __builtins__['_stack'] = __builtins__.get('_stack', ())
    __builtins__['_stack'] += ([kind, func_name],)
    try:
        yield
    except:
        raise
    finally:
        assert __builtins__['_stack'][:-1] == _backup
        __builtins__['_stack'] = _backup


def state():
    return (__builtins__.get('_stack') or ([None, None],))[-1][0]


def stack():
    return __builtins__.get('_stack') or ([None, None],)


def fn_type(kind, rules):
    def decorator(decoratee):
        def decorated(*a, **kw):
            name = '{}:{}()'.format(decoratee.__module__, decoratee.__name__)
            trace_funcs[kind]['in'](name, *a, **kw)
            rules()
            with state_layer(kind, name):
                val = decoratee(*a, **kw)
                assert val is not None, 'return data, not None, from function: {}'.format(name)
                trace_funcs[kind]['out'](name, val)
                return val
        return decorated
    return decorator


def glue_rules():
    assert state() != 'logic', 'logic cannot contain glue'
glue = fn_type('glue', glue_rules)


def flow_rules():
    assert state() != 'logic', 'logic cannot contain flow'
flow = fn_type('flow', flow_rules)


def logic_rules():
    assert state() != 'glue', 'glue cannot contain logic'
logic = fn_type('logic', logic_rules)


def inline(*funcs):
    """inline(f, g)(x) == g(f(x))"""
    funcs = [x if callable(x)
             else _unpack_partial(x)
             for x in funcs]
    def _fn(val):
        for func in funcs:
            val = func(val)
        return val
    return _fn


def thread(value, *funcs):
    """thread(123, f, g) == g(f(123))"""
    return inline(*funcs)(value)


def _unpack_partial(group):
    """takes a list like [fn, (arg1, ...), {kwarg1: val1, ...}] and
    returns a function of 1 arg, which will be the first pos arg to fn
    """
    args, kwargs = [], {}
    for obj in group[1:]:
        if isinstance(obj, (list, tuple)):
            args = obj
        elif isinstance(obj, dict):
            kwargs = obj
        else:
            raise ValueError('bad _unpack_partial group: {}'.format(group))
    def _fn(val):
        return group[0](val, *args, **kwargs)
    return _fn


_banned_attrs_dict = [
    '__setitem__',
    '__setattr__',
    'pop',
    'popitem',
    'update',
    'clear',
    'setdefault',
]


_immutable_types = [
    int,
    float,
    str,
    bytes,
    type(None),
    types.FunctionType,
    types.LambdaType,
]



def immutalize(decoratee):
    def decorated(*a, **kw):
        a = map(s.data.immutalize, a)
        kw = s.data.immutalize(kw)
        return decoratee(*a, **kw)
    return decorated
