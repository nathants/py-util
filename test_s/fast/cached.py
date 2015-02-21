from __future__ import print_function, absolute_import
import s
import pytest
import collections


def test_methods_are_illegal():
    class Foo(object):
        @s.cached.func
        def fn(self):
            pass
    with pytest.raises(AssertionError):
        Foo().fn()


def test_func():
    state = {'val': 0}
    @s.cached.func
    def fn():
        state['val'] += 1
    fn(), fn(), fn()
    assert state['val'] == 1


def test_is_cached():
    state = {'val': 0}
    @s.cached.func
    def fn():
        state['val'] += 1
    assert not s.cached.is_cached(fn)
    fn()
    assert s.cached.is_cached(fn)


def test_clear_func():
    state = {'val': 0}
    @s.cached.func
    def fn():
        state['val'] += 1
    fn(), fn(), fn()
    assert state['val'] == 1
    fn.clear_cache()
    fn(), fn(), fn()
    assert state['val'] == 2


def test_memoize():
    state = collections.Counter()
    @s.cached.memoize(2)
    def fn(arg):
        state[arg] += 1
    fn('a'), fn('a'), fn('b'), fn('b')
    assert state == {'a': 1, 'b': 1}


def test_without_optional_args_memoize():
    state = collections.Counter()
    @s.cached.memoize
    def fn(arg):
        state[arg] += 1
    fn('a'), fn('a'), fn('b'), fn('b')
    assert state == {'a': 1, 'b': 1}


def test_lru_is_correct_memoize():
    state = collections.Counter()
    @s.cached.memoize(2)
    def fn(arg):
        state[arg] += 1
        return arg
    fn('a')
    assert list(getattr(fn, s.cached._attr).items()) == [((('a',), frozenset()), 'a')]
    fn('b'),
    assert list(getattr(fn, s.cached._attr).items()) == [((('a',), frozenset()), 'a'), ((('b',), frozenset()), 'b')]
    fn('c')
    assert list(getattr(fn, s.cached._attr).items()) == [((('b',), frozenset()), 'b'), ((('c',), frozenset()), 'c')]
