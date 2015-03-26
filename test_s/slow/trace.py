from __future__ import print_function, absolute_import
import tornado.ioloop
import msgpack
import six
import tornado.gen
import time
import pytest
import json
import s.log
import s.web
import s.schema
import s.trace
import logging
import mock
import contextlib
import requests


@contextlib.contextmanager
def _capture_traces():
    s.log.setup.clear_cache()
    s.log.setup()
    results = []
    trace = lambda x: results.append(msgpack.loads(msgpack.dumps(x, default=s.trace._pretty_objects), encoding='utf-8'))
    with mock.patch.object(s.trace, '_trace', trace):
        yield results


def _check_schema(schemas, results):
    for result in results[len(schemas):]:
        raise Exception('no schema provided for next item:', s.dicts.take(result, ['name', 'fntype']))
    assert len(schemas) == len(results)
    for result, schema in zip(results, schemas):
        s.schema.validate(schema, (result['name'].split('.')[-1],
                                   result['fntype'],
                                   result['value'] if 'value' in result else result['args']))


def test_trace_coroutine():
    @tornado.gen.coroutine
    @s.trace.trace
    def main():
        future = tornado.concurrent.Future()
        future.set_result('asdf')
        val = yield future
        raise tornado.gen.Return(val + '!!')
    with _capture_traces() as results:
        assert s.async.run_sync(main) == 'asdf!!'
    _check_schema([('main', 'gen', [object]),
                   ('main', 'gen.yield', '<Future>'),
                   ('main', 'gen.send', ['asdf']),
                   ('main', 'gen', 'asdf!!')],
                  results)


def test_trace_coroutine_nested():
    @tornado.gen.coroutine
    @s.trace.trace
    def main():
        val = yield add_one(1)
        raise tornado.gen.Return(val)
    @tornado.gen.coroutine
    @s.trace.trace
    def add_one(x):
        yield tornado.gen.moment
        raise tornado.gen.Return(x + 1)
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
    @tornado.gen.coroutine
    @s.trace.trace
    def handler(request):
        yield tornado.gen.moment
        assert request['verb'] == 'get'
        raise tornado.gen.Return({'headers': {'foo': 'bar'},
                                  'code': 200,
                                  'body': 'ok'})
    app = s.web.app([('/', {'GET': handler})])
    with s.web.test(app, poll=False, use_thread=True) as url:
        @tornado.gen.coroutine
        def main():
            yield tornado.gen.sleep(.1) # TODO this should be evented s.web.wait_for_http
            with _capture_traces() as results:
                resp = yield s.web.get(url)
            assert resp['body'] == 'ok'
            assert resp['headers']['foo'] == 'bar'
            tornado.ioloop.IOLoop.instance().stop()
            raise tornado.gen.Return(results)
        results = s.async.run_sync(main)
    _check_schema([('handler', 'gen', [object]),
                   ('handler', 'gen.yield', '<Future>'),
                   ('handler', 'gen.send', [None]),
                   ('handler', 'gen', {'body': 'ok',
                                       'code': 200,
                                       'headers': {object: object}})],
                  results)


def test_trace():
    @s.trace.trace
    def fn(x):
        return x + 1

    with _capture_traces() as results:
        fn(1)

    assert results[0]['args'] == [1]
    assert results[1]['value'] == 2
    assert len(results) == 2


def test_trace_fn_returning_fn():
    @s.trace.trace
    def fn():
        return lambda: None
    with _capture_traces() as results:
        fn()
    assert results[1]['value'] == '<function>'


def test_trace_fn_returning_reverseiterator():
    pass


def test_freezes_trace():
    @s.trace.trace
    def fn(x):
        x[1] = 2
    with pytest.raises(ValueError):
        fn({})


def test_trace_raise():
    @s.trace.trace
    def trace():
        1 / 0
    with pytest.raises(ZeroDivisionError):
        trace()


def test_trace_gen_raise():
    @s.trace.trace
    def trace():
        for x in range(3):
            yield x
        1 / 0
    with pytest.raises(ZeroDivisionError):
        for i, x in enumerate(trace()):
            assert i == x
