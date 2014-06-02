from __future__ import absolute_import, print_function
import os
import inspect
import pprint
import sys
import functools
import traceback
import json
import contextlib
import logging
import time
import types
import s


_state = {}

_json_types = (list,
               str,
               dict,
               int,
               float,
               tuple)
with s.exceptions.ignore():
    _json_types += (
        type({}.items()),
        type({}.keys()),
        type({}.values()),
    )
try:
    _json_types += (unicode,)
except:
    _json_types += (bytes,)


def _stringify(val):
    if isinstance(val, dict):
        return {_stringify(k): _stringify(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple, set)):
        return [_stringify(x) for x in val]
    elif isinstance(val, _json_types):
        return val
    else:
        return str(val)


def _trace(val):
    try:
        text = json.dumps(val)
    except:
        try:
            text = json.dumps(_stringify(val))
        except:
            logging.error('bad val:', val)
            raise
    logging.trace(text)


trace_funcs = {
    'logic': {
        'in': lambda name, fntype, *a, **kw: _trace({
            'name': name,
            'direction': 'in',
            'fntype': fntype,
            'args': a,
            'kwargs': kw,
            'time': time.time(),
            'stack': stack(),
            'cwd': os.getcwd(),
        }),
        'out': lambda name, fntype, val=None, traceback=None: _trace({
            'name': name,
            'direction': 'out',
            'fntype': fntype,
            'value': val,
            'time': time.time(),
            'stack': stack(),
            'traceback': traceback,
            'cwd': os.getcwd(),
        })
    }
}


for name in ['glue', 'flow', 'badfunc']:
    trace_funcs[name] = trace_funcs['logic']


@contextlib.contextmanager
def state_layer(name):
    _bak = _state['_stack'] = _state.get('_stack') or ()
    _state['_stack'] += (name,)
    try:
        yield
    except:
        raise
    finally:
        _val = _state['_stack'][:-1]
        assert _val == _bak, '{} != {}'.format(_val, _bak)
        _state['_stack'] = _bak


def state(offset=0):
    try:
        return (_state.get('_stack') or ())[-(1 + offset)].split(':')[0]
    except IndexError:
        return ()


def stack():
    return _state.get('_stack') or ()


def _module_name(fn):
    module = fn.__module__
    with s.exceptions.ignore():
        if module == '__main__':
            for x in range(20):
                _module = '.'.join(__file__.split('.')[0].split('/')[x:])
                if _module in sys.modules:
                    return _module
    return module


def make_fn_type(kind, rules, skip_return_check=False):
    def decorator(decoratee):
        if inspect.isgeneratorfunction(decoratee):
            return _gen_type(decoratee, kind, rules)
        fn = _fn_type(decoratee, kind, rules, skip_return_check)
        fn.__doc__ = _format_argspec(decoratee) + ('\n' + fn.__doc__ if fn.__doc__ else '')
        return fn
    return decorator


def _format_argspec(fn):
    args, varargs, keywords, defaults = inspect.getargspec(fn)
    if defaults:
        args = args[:len(defaults)]
        defaults = zip(args[-len(defaults):], defaults)
        defaults = ['{}={}'.format(k, repr(v)) for k, v in defaults]
    val = ', '.join(args)
    if defaults:
        val += ', ' + ', '.join(defaults)
    if varargs:
        val += ', *{}'.format(varargs)
    if keywords:
        val += ', **{}'.format(keywords)
    return 'def {}({})'.format(fn.__name__, val)


def _fn_type(decoratee, kind, rules, skip_return_check):
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        name = '{}:{}:{}'.format(kind, _module_name(decoratee), decoratee.__name__)
        trace_funcs[kind]['in'](name, 'fn', *a, **kw)
        with state_layer(name):
            try:
                rules()
                val = decoratee(*a, **kw)
                assert type(val) != types.GeneratorType
            except:
                trace_funcs[kind]['out'](name, 'fn', traceback=traceback.format_exc())
                raise
            else:
                assert skip_return_check or val is not None, 'return data, not None, from function: {}'.format(name)
            trace_funcs[kind]['out'](name, 'fn', val=val)
        return val
    return decorated


def _gen_type(decoratee, kind, rules):
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        name = '{}:{}:{}'.format(kind, _module_name(decoratee), decoratee.__name__)
        trace_funcs[kind]['in'](name, 'gen', *a, **kw)
        generator = decoratee(*a, **kw)
        assert type(generator) == types.GeneratorType
        to_send = None
        while True:
                with state_layer(name):
                    try:
                        rules()
                        to_yield = generator.send(to_send)
                    except StopIteration as e:
                        trace_funcs[kind]['out'](name, 'gen', val=e)
                        raise
                    except:
                        trace_funcs[kind]['out'](name, 'gen', traceback=traceback.format_exc())
                        raise
                    else:
                        trace_funcs[kind]['out'](name, 'gen', val=to_yield)
                to_send = yield to_yield
    return decorated


def _rule_violation_message():
    caller = s.hacks.get_caller(4)
    with open(caller.filename) as fio:
        line = fio.read().splitlines()[caller.linenum - 1].strip()
    return '\n'.join([
        '',
        '[{}:{}] {}'.format(caller.filename, caller.linenum, line),
        'attempted illegal transtion: {} -> {}'.format(*stack()[-2:]),
        'stack:\n{}'.format(pprint.pformat(stack())),
        '',
    ])


def glue_rules():
    assert state(offset=1) != 'logic', 'logic cannot contain glue\n{}'.format(_rule_violation_message())
glue = make_fn_type('glue', glue_rules)


# todo, define better the difference between glue and flow. are two types necessary?
def flow_rules():
    assert state(offset=1) != 'logic', 'logic cannot contain flow\n{}'.format(_rule_violation_message())
flow = make_fn_type('flow', flow_rules)


def logic_rules():
    assert state(offset=1) != 'glue', 'glue cannot contain logic\n{}'.format(_rule_violation_message())
logic = make_fn_type('logic', logic_rules)


badfunc = make_fn_type('badfunc', lambda: True, skip_return_check=True) # use for tests, and other non-system functions


def inline(*funcs):
    """inline(f, g)(x) == g(f(x))"""
    for fn in funcs:
        assert callable(fn), '{} is not callable'.format(fn)
    def _fn(val):
        for func in funcs:
            val = func(val)
        return val
    return _fn


def thrush(value, *funcs):
    """thread(123, f, g) == g(f(123))"""
    return inline(*funcs)(value)


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
