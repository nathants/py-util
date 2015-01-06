from __future__ import print_function, absolute_import
import pytest
import json
import s
import logging
import mock
import contextlib
import requests


@contextlib.contextmanager
def _capture_traces():
    s.log.setup.clear_cache()
    s.log.setup()
    results = []
    trace = lambda x: results.append(json.loads(x))
    with mock.patch.object(logging, 'trace', trace):
        yield results


def _check_schema(schemas, results):
    for result in results[len(schemas):]:
        raise Exception('no schema provided for next item:', s.dicts.take(result, ['name', 'fntype']))
    for result, schema in zip(results, schemas):
        s.schema.validate(schema, (result['name'].split(':')[-1],
                                   result['fntype'],
                                   result['value'] if 'value' in result else result['args']))


def test_trace_coroutine():
    @s.async.coroutine
    def main():
        future = s.async.Future()
        future.set_result('asdf')
        val = yield future
        raise s.async.Return(val + '!!')
    with _capture_traces() as results:
        assert s.async.run_sync(main) == 'asdf!!'
    _check_schema([('main', 'gen', [object]),
                   ('main', 'gen.yield', '<Future>'),
                   ('main', 'gen.send', ['asdf']),
                   ('main', 'gen', 'asdf!!')],
                  results)


def test_trace_coroutine_nested():
    @s.async.coroutine
    def main():
        val = yield add_one(1)
        raise s.async.Return(val)
    @s.async.coroutine
    def add_one(x):
        yield s.async.moment
        raise s.async.Return(x + 1)
    with _capture_traces() as results:
        assert s.async.run_sync(main) == 2
    _check_schema([('main', 'gen', [object]),            # call main
                   ('add_one', 'gen', [1]),              # call add_one
                   ('add_one', 'gen.yield', '<Future>'), # add_one yields moment
                   ('main', 'gen.yield', '<Future>'),    # main yields add_one
                   ('add_one', 'gen.send', [None]),      # send moments result to add_one
                   ('add_one', 'gen', 2),                # add_one returns
                   ('main', 'gen.send', [2]),            # send add_ones result to main
                   ('main', 'gen', 2)],                  # main returns
                  results)


def test_trace_web():
    s.log.setup.clear_cache()
    s.log.setup()
    s.shell.run('rm', s.log._trace_path)
    @s.async.coroutine
    def handler(request):
        yield s.async.moment
        assert request['verb'] == 'get'
        raise s.async.Return({'headers': {'foo': 'bar'},
                              'code': 200,
                              'body': 'ok'})
    app = s.web.app([('/', {'GET': handler})])
    with s.web.test(app, poll=False) as url:
        import time
        time.sleep(.1)
        resp = requests.get(url)
        assert resp.text == 'ok'
        assert resp.headers['foo'] == 'bar'
    with open(s.log._trace_path) as f:
        results = [json.loads(x) for x in f.read().splitlines()]
    _check_schema([('handler', 'gen', [object]),
                   ('handler', 'gen.yield', '<Future>'),
                   ('handler', 'gen.send', [None]),
                   ('handler', 'gen', {'body': 'ok',
                                       'code': 200,
                                       'headers': {object: object}})],
                  results)


def test_trace():
    @s.trace.glue
    def fn(x):
        return x + 1

    with _capture_traces() as results:
        fn(1)

    assert results[0]['args'] == [1]
    assert results[1]['value'] == 2
    assert len(results) == 2


def test_trace_fn_returning_fn():
    @s.trace.logic
    def fn():
        return lambda: None
    with _capture_traces() as results:
        fn()
    assert results[1]['value'] == '<function>'


def test_trace_fn_returning_reverseiterator():
    pass


def test_freezes_logic():
    @s.trace.logic
    def fn(x):
        x[1] = 2
    with pytest.raises(ValueError):
        fn({})


def test__stack():
    start = s.trace._stack()
    @s.trace.logic
    def fn1():
        assert s.trace._stack() == ('logic:{}:fn1'.format(__name__),)
        return fn2()
    @s.trace.logic
    def fn2():
        assert s.trace._stack() == ('logic:{}:fn1'.format(__name__),
                                    'logic:{}:fn2'.format(__name__))
        return True
    fn1()
    assert s.trace._stack() == start


def test_flow_in_logic():
    @s.trace.glue
    def flow():
        return True
    @s.trace.logic
    def logic():
        flow()
    with pytest.raises(AssertionError):
        logic()


def test_glue_in_logic():
    @s.trace.io
    def glue():
        return True
    @s.trace.logic
    def logic():
        return glue()
    with pytest.raises(AssertionError):
        logic()


def test_logic_generator():
    @s.trace.logic
    def logic():
        for x in range(3):
            assert s.trace._stack() == ('logic:test_s.slow.trace:logic',)
            yield x

    for i, x in enumerate(logic()):
        assert i == x, str([i, x])
        assert s.trace._stack() == (), str(s.trace._stack(), ())


def test_logic_raise():
    @s.trace.logic
    def logic():
        1 / 0
    with pytest.raises(ZeroDivisionError):
        logic()


def test_logic_gen_raise():
    @s.trace.logic
    def logic():
        for x in range(3):
            yield x
        1 / 0
    with pytest.raises(ZeroDivisionError):
        for i, x in enumerate(logic()):
            assert i == x


def test_logic_return_none():
    @s.trace.logic
    def fn():
        return None
    with pytest.raises(AssertionError):
        fn()
