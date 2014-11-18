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
import s
import tornado.concurrent
import concurrent.futures


_state = {}


_future_types = (tornado.concurrent.Future,
                 concurrent.futures.Future)

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


def _jsonify(val):
    if isinstance(val, dict):
        return {_jsonify(k): _jsonify(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [_jsonify(x) for x in val]
    elif isinstance(val, _json_types):
        return val
    else:
        val = str(val)
        if ' at 0x' in val:
            val = val.split()[0].split('.')[-1]
        return '<{}>'.format(val.strip('<>'))


def _trace(val):
    try:
        text = json.dumps(val)
    except:
        try:
            text = json.dumps(_jsonify(val))
        except:
            text = json.dumps('failed to jsonify: {}'.format(val))
    if s.cached.is_cached(s.log.setup):
        getattr(logging, 'trace', lambda x: None)(text)


_trace_funcs = {
    'logic': {
        'in': lambda name, fntype, *a, **kw: _trace({
            'name': name,
            'direction': 'in',
            'fntype': fntype,
            'args': a,
            'kwargs': kw,
            'time': time.time(),
            'stack': _stack(),
            'cwd': os.getcwd(),
        }),
        'out': lambda name, fntype, val=None, traceback=None: _trace({
            'name': name,
            'direction': 'out',
            'fntype': fntype,
            'value': val,
            'time': time.time(),
            'stack': _stack(),
            'traceback': traceback,
            'cwd': os.getcwd(),
        })
    }
}


for name in ['glue', 'flow', 'bad']:
    _trace_funcs[name] = _trace_funcs['logic']


@contextlib.contextmanager
def _state_layer(name):
    _backup_stack = _state['_stack'] = _state.get('_stack') or ()
    _state['_stack'] += (name,)
    try:
        yield
    except:
        raise
    finally:
        _val = _state['_stack'][:-1]
        assert _val == _backup_stack, 'stack mutated during function call: {} != {}'.format(_val, _backup_stack)
        _state['_stack'] = _backup_stack


def _get_state(offset=0):
    try:
        return (_state.get('_stack') or ())[-(1 + offset)].split(':')[0]
    except IndexError:
        return ()


def _stack():
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


def _make_traceable_type(kind, rules, immutalize=True):
    def decorator(decoratee):
        if inspect.isgeneratorfunction(decoratee):
            return _gen_type(decoratee, kind, rules, immutalize)
        return _fn_type(decoratee, kind, rules, immutalize)
    return decorator


def _fn_type(decoratee, kind, rules, immutalize):
    name = '{}:{}:{}'.format(kind, _module_name(decoratee), decoratee.__name__)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        _trace_funcs[kind]['in'](name, 'fn', *a, **kw)
        with _state_layer(name):
            try:
                if immutalize:
                    a, kw = s.data.immutalize(a), s.data.immutalize(kw)
                rules()
                val = decoratee(*a, **kw)
                if immutalize:
                    val = s.data.immutalize(val)
                assert val is not None, 'you cannot return None from: {name}'.format(**locals())
            except:
                _trace_funcs[kind]['out'](name, 'fn', traceback=traceback.format_exc())
                raise
            _trace_funcs[kind]['out'](name, 'fn', val=val)
        return val
    return decorated


def _gen_type(decoratee, kind, rules, immutalize):
    name = '{}:{}:{}'.format(kind, _module_name(decoratee), decoratee.__name__)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        _trace_funcs[kind]['in'](name, 'gen', *a, **kw)
        if immutalize:
            a, kw = s.data.immutalize(a), s.data.immutalize(kw)
        generator = decoratee(*a, **kw)
        to_send = None
        first_send = True
        while True:
                with _state_layer(name):
                    try:
                        rules()
                        if immutalize:
                            to_send = s.data.immutalize(to_send)
                        if not first_send:
                            _trace_funcs[kind]['in'](name, 'gen.send', to_send)
                        first_send = False
                        to_yield = generator.send(to_send)
                        if immutalize and not _is_futury(to_yield):
                            to_yield = s.data.immutalize(to_yield)
                    except (s.async.Return, StopIteration) as e:
                        _trace_funcs[kind]['out'](name, 'gen', val=getattr(e, 'value', None))
                        raise e
                    except:
                        _trace_funcs[kind]['out'](name, 'gen', traceback=traceback.format_exc())
                        raise
                    else:
                        _trace_funcs[kind]['out'](name, 'gen.yield', val=to_yield)
                to_send = yield to_yield
    return decorated


def _is_futury(obj):
    if isinstance(obj, _future_types):
        return True
    elif isinstance(obj, (list, tuple)) and all(isinstance(x, _future_types) for x in obj):
        return True
    elif isinstance(obj, dict) and all(isinstance(x, _future_types) for x in obj.values()):
        return True
    else:
        return False


def _rule_violation_message():
    caller = s.hacks.get_caller(4)
    with open(caller['filename']) as _fio:
        line = _fio.read().splitlines()[caller['linenum'] - 1].strip()
    return '\n'.join([
        '',
        '[{}:{}] {}'.format(caller['filename'], caller['linenum'], line),
        'attempted illegal transtion: {} -> {}'.format(*_stack()[-2:]),
        '_stack:\n{}'.format(pprint.pformat(_stack())),
        '',
    ])


def _glue_rules():
    assert _get_state(offset=1) != 'logic', 'logic cannot contain glue\n{}'.format(_rule_violation_message())
glue = _make_traceable_type('glue', _glue_rules)


# todo, define better the difference between glue and flow. are two types necessary?
def _flow_rules():
    assert _get_state(offset=1) != 'logic', 'logic cannot contain flow\n{}'.format(_rule_violation_message())
flow = _make_traceable_type('flow', _flow_rules)


def _logic_rules():
    assert _get_state(offset=1) != 'glue', 'glue cannot contain logic\n{}'.format(_rule_violation_message())
logic = _make_traceable_type('logic', _logic_rules)


bad = _make_traceable_type('bad', lambda: True, immutalize=False) # use for tests, and other non-system functions


def inline(*funcs):
    for fn in funcs:
        assert callable(fn), '{} is not callable'.format(fn)
    def _fn(val):
        for func in funcs:
            val = func(val)
        return val
    return _fn


def pipe(value, *funcs):
    return inline(*funcs)(value)


def name(fn):
    with s.exceptions.ignore():
        return '{}.{}'.format(fn.__module__, fn.__name__)
    with s.exceptions.ignore():
        return fn.__name__
    with s.exceptions.ignore():
        return str(fn)
    return fn


def source(fn):
    try:
        filename, linenum = fn.func_code.co_filename, fn.func_code.co_firstlineno
        with open(filename) as _file:
            text = _file.read().splitlines()[linenum - 1]
            return '{filename}:{linenum} => {text}'.format(**locals())
    except:
        return name(fn)
