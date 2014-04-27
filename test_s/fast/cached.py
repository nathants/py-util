import s
import collections


def test_func():
    state = {'val': 0}
    @s.cached.func
    def fn():
        state['val'] += 1
        return state['val']
    assert state['val'] == 0
    fn()
    assert state['val'] == 1
    fn()
    assert state['val'] == 1


def test_clear():
    state = {'val': 0}
    @s.cached.func
    def fn():
        state['val'] += 1
        return state['val']
    assert fn() == 1
    assert fn() == 1
    fn.clear_cache()
    assert fn() == 2
    assert fn() == 2


def test_memoize():
    state = collections.Counter()
    @s.cached.memoize(2)
    def fn(arg):
        state[arg] += 1
        return arg
    assert fn('a') == 'a'
    assert fn('b') == 'b'
    assert state == {'a': 1, 'b': 1}
    assert fn('a') == 'a'
    assert fn('b') == 'b'
    assert state == {'a': 1, 'b': 1}
    assert fn._data == {(('a', ), ()): 'a', (('b',), ()): 'b'}
    assert fn('c') == 'c'
    assert fn._data == {(('b',), ()): 'b', (('c', ), ()): 'c', }
