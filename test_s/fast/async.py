from __future__ import print_function, absolute_import
import pytest
import s
from test_s.slow import flaky


@flaky
def test_coroutines_do_not_persist_between_runsync_calls():
    state = []
    @s.async.coroutine
    def mutator():
        while True:
            state.append(None)
            yield s.async.moment

    @s.async.coroutine
    def one():
        mutator()
        yield s.async.moment

    @s.async.coroutine
    def two():
        yield s.async.moment

    assert len(state) == 0
    s.async.run_sync(one)
    assert len(state) == 3
    s.async.run_sync(two)
    assert len(state) == 3


@flaky
def test_coroutine_return():
    @s.async.coroutine
    def fn():
        yield s.async.moment
        raise s.async.Return(123)
    assert s.async.run_sync(fn) == 123


@flaky
def test_coroutine():
    state = []

    @s.async.coroutine
    def zero():
        for i in range(2):
            state.append(i)
            yield s.async.moment

    @s.async.coroutine
    def ten():
        zero()
        for i in range(10, 12):
            state.append(i)
            yield s.async.moment

    s.async.run_sync(ten)
    assert state == [0, 10, 1, 11]


@flaky
def test_coroutines_must_be_generators():
    with pytest.raises(AssertionError):
        @s.async.coroutine
        def main():
            pass


def test_exception_handling():
    @s.async.coroutine(AssertionError)
    def throw():
        yield s.async.moment
        assert False

    @s.async.coroutine(AssertionError)
    def fn():
        try:
            yield throw()
        except:
            raise s.async.Return('yes')

    assert s.async.run_sync(fn) == 'yes'
