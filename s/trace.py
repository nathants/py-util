from __future__ import print_function, absolute_import
import os
import inspect
import pprint
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


def _trace(val):
    try:
        text = json.dumps(val)
    except:
        try:
            text = json.dumps(s.data.jsonify(val))
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


for name in ['io', 'glue', 'mutable']:
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


def _traceable(kind, rules, freeze=True):
    def decorator(decoratee):
        if inspect.isgeneratorfunction(decoratee):
            return _gen_type(decoratee, kind, rules, freeze)
        return _fn_type(decoratee, kind, rules, freeze)
    return decorator


def _fn_type(decoratee, kind, rules, freeze):
    name = '{}:{}:{}'.format(kind, s.func.module_name(decoratee), decoratee.__name__)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        _trace_funcs[kind]['in'](name, 'fn', *a, **kw)
        with _state_layer(name):
            try:
                if freeze:
                    a, kw = s.data.freeze(a), s.data.freeze(kw)
                rules()
                val = decoratee(*a, **kw)
                if freeze:
                    val = s.data.freeze(val)
            except:
                _trace_funcs[kind]['out'](name, 'fn', traceback=traceback.format_exc())
                raise
            _trace_funcs[kind]['out'](name, 'fn', val=val)
        return val
    return decorated


def _is_select_result(obj):
    return s.schema.is_valid(s.sock.schemas.select_result, obj, freeze=False)


def _gen_type(decoratee, kind, rules, freeze):
    name = '{}:{}:{}'.format(kind, s.func.module_name(decoratee), decoratee.__name__)
    @functools.wraps(decoratee)
    def decorated(*a, **kw):
        _trace_funcs[kind]['in'](name, 'gen', *a, **kw)
        if freeze:
            a, kw = s.data.freeze(a), s.data.freeze(kw)
        generator = decoratee(*a, **kw)
        to_send = None
        first_send = True
        while True:
                with _state_layer(name):
                    try:
                        rules()
                        if freeze and not _is_select_result(to_send):
                            to_send = s.data.freeze(to_send)
                        if not first_send:
                            _trace_funcs[kind]['in'](name, 'gen.send', to_send)
                        first_send = False
                        to_yield = generator.send(to_send)
                        if freeze and not _is_futury(to_yield):
                            to_yield = s.data.freeze(to_yield)
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


def _io_rules():
    assert _get_state(offset=1) != 'logic', 'logic cannot contain io\n{}'.format(_rule_violation_message())
io = _traceable('io', _io_rules)


def _glue_rules():
    assert _get_state(offset=1) != 'logic', 'logic cannot contain glue\n{}'.format(_rule_violation_message())
glue = _traceable('glue', _glue_rules)


def _logic_rules():
    assert _get_state(offset=1) != 'io', 'io cannot contain logic\n{}'.format(_rule_violation_message())
logic = _traceable('logic', _logic_rules)


mutable = _traceable('mutable', lambda: True, freeze=False) # use for tests, and other non-system functions
