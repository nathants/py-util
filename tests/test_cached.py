import util.cached
import pytest
import collections


def test_methods_are_illegal():
    class Foo(object):
        @util.cached.disk
        def fn():
            pass
    with pytest.raises(AssertionError):
        Foo().fn()


def test_disk():
    state = {'val': 0}
    @util.cached.disk
    def fn():
        state['val'] += 1
        return 'foo'
    fn.clear_cache()
    assert [fn(), fn(), fn()] == ['foo', 'foo', 'foo']
    assert state['val'] == 1


def test_disk_memoize():
    state = {'args': []}
    @util.cached.disk_memoize
    def fn(a):
        state['args'].append(a)
        return a
    fn.clear_cache()
    assert [fn(1), fn(2), fn(1), fn(2)] == [1, 2, 1, 2]
    assert state['args'] == [1, 2]


def test_methods_are_illegal():
    class Foo(object):
        @util.cached.func
        def fn(self):
            pass
    with pytest.raises(AssertionError):
        Foo().fn()


def test_func():
    state = {'val': 0}
    @util.cached.func
    def fn():
        state['val'] += 1
    fn(), fn(), fn()
    assert state['val'] == 1


def test_is_cached():
    state = {'val': 0}
    @util.cached.func
    def fn():
        state['val'] += 1
    assert not util.cached.is_cached(fn)
    fn()
    assert util.cached.is_cached(fn)


def test_clear_func():
    state = {'val': 0}
    @util.cached.func
    def fn():
        state['val'] += 1
    fn(), fn(), fn()
    assert state['val'] == 1
    fn.clear_cache()
    fn(), fn(), fn()
    assert state['val'] == 2


def test_memoize():
    state = collections.Counter()
    @util.cached.memoize(2)
    def fn(arg):
        state[arg] += 1
    fn('a'), fn('a'), fn('b'), fn('b')
    assert state == {'a': 1, 'b': 1}


def test_without_optional_args_memoize():
    state = collections.Counter()
    @util.cached.memoize
    def fn(arg):
        state[arg] += 1
    fn('a'), fn('a'), fn('b'), fn('b')
    assert state == {'a': 1, 'b': 1}


def test_lru_is_correct_memoize():
    state = collections.Counter()
    @util.cached.memoize(2)
    def fn(arg):
        state[arg] += 1
        return arg
    fn('a')
    assert list(getattr(fn, util.cached._attr).items()) == [((('a',), frozenset()), 'a')]
    fn('b'),
    assert list(getattr(fn, util.cached._attr).items()) == [((('a',), frozenset()), 'a'), ((('b',), frozenset()), 'b')]
    fn('c')
    assert list(getattr(fn, util.cached._attr).items()) == [((('b',), frozenset()), 'b'), ((('c',), frozenset()), 'c')]
