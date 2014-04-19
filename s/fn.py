from __future__ import absolute_import
import functools
import traceback
import contextlib
import logging
import time
import types
import s


_state = {}


def _pretty(name, char, offset=0):
    return (name.rjust(40) + '|' + '-' * (len(stack()) - offset) + char + '   ').ljust(80)


trace_funcs = {
    'logic': {
        'in': lambda name, *a, **kw: logging.debug([
            _pretty(name, '>'),
            {'args': a,
             'direction': 'in',
             'kwargs': kw,
             'time': time.time(),
             'state': state(),
             'stack': _format_stack(stack())}
        ]),
        'out': lambda name, val=None, traceback=None: logging.debug([
            _pretty(name, '<', 1),
            {'value': val,
             'direction': 'out',
             'time': time.time(),
             'state': state(),
             'stack': _format_stack(stack()),
             'traceback': traceback.splitlines() if traceback else None}
        ])
    }
}


# trace_funcs['glue'] = trace_funcs['flow'] = trace_funcs['logic']
for name in ['glue', 'flow', 'badfunc']:
    trace_funcs[name] = trace_funcs['logic']


def _format_stack(val):
    return [':'.join(map(str, x)) for x in val]


@contextlib.contextmanager
def state_layer(kind, func_name):
    _bak = _state['_stack'] = _state.get('_stack', ())
    _state['_stack'] += ([kind, func_name],)
    try:
        yield
    except:
        raise
    finally:
        _val = _state['_stack'][:-1]
        assert _val == _bak, '{} != {}'.format(_val, _bak)
        _state['_stack'] = _bak


def state():
    try:
        return (_state.get('_stack') or ())[-1][0]
    except IndexError:
        return ()


def stack():
    return _state.get('_stack') or ()


def fn_type(kind, rules, skip_return_check=False):
    def decorator(decoratee):
        @functools.wraps(decoratee)
        def decorated(*a, **kw):
            name = '{}:{}()'.format(decoratee.__module__, decoratee.__name__)
            trace_funcs[kind]['in'](name, *a, **kw)
            rules()
            with state_layer(kind, name):
                try:
                    val = decoratee(*a, **kw)
                except:
                    trace_funcs[kind]['out'](name, traceback=traceback.format_exc())
                    raise
                else:
                    trace_funcs[kind]['out'](name, val)
                    assert skip_return_check or val is not None, 'return data, not None, from function: {}'.format(name)
                    return val
        return decorated
    return decorator


def glue_rules():
    assert state() != 'logic', 'logic cannot contain glue: {}'.format(s.hacks.get_caller(3))
glue = fn_type('glue', glue_rules)


# todo, define better the difference between glue and flow. are two types necessary?
def flow_rules():
    assert state() != 'logic', 'logic cannot contain flow: {}'.format(s.hacks.get_caller(3))
flow = fn_type('flow', flow_rules)


def logic_rules():
    assert state() != 'glue', 'glue cannot contain logic: {}'.format(s.hacks.get_caller(3))
logic = fn_type('logic', logic_rules)


badfunc = fn_type('badfunc', lambda: True, skip_return_check=True) # use for tests, and other non-system functions


def inline(*funcs):
    """inline(f, g)(x) == g(f(x))"""
    for fn in funcs:
        assert callable(fn), '{} is not callable'.format(fn)
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
