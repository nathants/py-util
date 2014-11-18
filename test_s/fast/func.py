import pytest
import json
import s
import logging
import mock
import contextlib


@contextlib.contextmanager
def _capture_traces():
    s.log.setup.clear_cache()
    s.log.setup()
    results = []
    trace = lambda x: results.append(json.loads(x))
    with mock.patch.object(logging, 'trace', trace):
        yield results


def test_trace():
    @s.func.flow
    def fn(x):
        return x + 1

    with _capture_traces() as results:
        fn(1)

    assert results[0]['args'] == [1]
    assert results[1]['value'] == 2


def test_trace_coroutine():
    @s.async.coroutine
    def main():
        future = s.async.Future()
        future.set_result('asdf')
        val = yield future
        raise s.async.Return(val + '!!')
    with _capture_traces() as results:
        assert s.async.run_sync(main) == 'asdf!!'
    assert [x['fntype'] for x in results] == ['gen', 'gen.yield', 'gen.send', 'gen']
    assert [x['value'] if 'value' in x else x['args'] for x in results] == [[], '<Future>', ['asdf'], 'asdf!!']


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
    val = [('main', 'gen', []),                  # call main
           ('add_one', 'gen', [1]),              # call add_one
           ('add_one', 'gen.yield', '<Future>'), # add_one yields moment
           ('main', 'gen.yield', '<Future>'),    # main yields add_one
           ('add_one', 'gen.send', [None]),      # send moments result to add_one
           ('add_one', 'gen', 2),                # add_one returns
           ('main', 'gen.send', [2]),            # send add_ones result to main
           ('main', 'gen', 2)]                   # main returns
    assert val == [(x['name'].split(':')[-1],
                    x['fntype'],
                    x['value'] if 'value' in x else x['args'])
                   for x in results]


# @pytest.mark.only
def test_trace_fn_returning_fn():
    @s.func.logic
    def fn():
        return lambda: None
    with _capture_traces() as results:
        fn()
    assert results[1]['value'] == '<function>'


def test_trace_fn_returning_reverseiterator():
    pass


def test_immutalizes_logic():
    @s.func.logic
    def fn(x):
        x[1] = 2
    with pytest.raises(ValueError):
        fn({})


def test__stack():
    start = s.func._stack()
    @s.func.logic
    def fn1():
        assert s.func._stack() == ('logic:{}:fn1'.format(__name__),)
        return fn2()
    @s.func.logic
    def fn2():
        assert s.func._stack() == ('logic:{}:fn1'.format(__name__),
                                   'logic:{}:fn2'.format(__name__))
        return True
    fn1()
    assert s.func._stack() == start


def test_flow_in_logic():
    @s.func.flow
    def flow():
        return True
    @s.func.logic
    def logic():
        flow()
    with pytest.raises(AssertionError):
        logic()


def test_glue_in_logic():
    @s.func.glue
    def glue():
        return True
    @s.func.logic
    def logic():
        return glue()
    with pytest.raises(AssertionError):
        logic()


def _plus_one(x, *a):
    return x + 1


def _times_two(x):
    return x * 2


def _three_minus(x):
    return 3 - x


def test_inline():
    assert s.func.inline(_plus_one, _times_two, _three_minus)(1) == -1
    assert s.func.inline(_plus_one, _times_two, _three_minus)(1) == _three_minus(_times_two(_plus_one(1)))
    assert s.func.inline(_three_minus, _times_two, _plus_one)(1) == 5
    assert s.func.inline(_three_minus, _times_two, _plus_one)(1) == _plus_one(_times_two(_three_minus(1)))


def test_inline_noncallable():
    with pytest.raises(AssertionError):
        s.func.inline(_three_minus, _times_two, 1)(1)


def test_pipe():
    assert s.func.pipe(1, _plus_one, _times_two, _three_minus) == -1


def test_thread_noncallable():
    with pytest.raises(AssertionError):
        s.func.pipe(1, _plus_one, _times_two, 2)


def test_logic_generator():
    @s.func.logic
    def logic():
        for x in range(3):
            assert s.func._stack() == ('logic:test_s.fast.func:logic',)
            yield x

    for i, x in enumerate(logic()):
        assert i == x
        assert s.func._stack() == ()


def test_logic_raise():
    @s.func.logic
    def logic():
        1 / 0
    with pytest.raises(ZeroDivisionError):
        logic()


def test_logic_gen_raise():
    @s.func.logic
    def logic():
        for x in range(3):
            yield x
        1 / 0
    with pytest.raises(ZeroDivisionError):
        for i, x in enumerate(logic()):
            assert i == x


def test_return_none():
    @s.func.logic
    def fn():
        return None
    with pytest.raises(AssertionError):
        fn()
