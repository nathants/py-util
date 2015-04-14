import s.dicts
import pytest
import operator


def test_update_in():
    assert s.dicts.update_in({'a': {'b': 'c'}}, ['a', 'b'], operator.add, '!') == {'a': {'b': 'c!'}}
    assert s.dicts.update_in({'a': {'b': 'c'}}, 'a', str) == {'a': "{'b': 'c'}"}


def test_get():
    assert s.dicts.get({'a': {'b': 'c'}}, ['a', 'b']) == 'c'


def test_set():
    assert s.dicts.set({}, ['a', 'b'], 'c') == {'a': {'b': 'c'}}


def test_merge_freezes():
    assert s.dicts.merge({'a': 'b'}, {'a': ['c', 'd']}) == {'a': ['c', 'd']}


def test_merge():
    assert s.dicts.merge({'a': {'b': 'c'}},
                         {'a': {'d': 'e'}}) == {'a': {'b': 'c',
                                                'd': 'e'}}


def test_merge_dict_with_nondict():
    assert s.dicts.merge({'a': 'b'}, {'a': {'b': 'c'}}) == {'a': {'b': 'c'}}


def test_mutability_merge_a():
    a = {'a': 'b'}
    assert s.dicts.merge(a, {'a': 'c'}) == {'a': 'c'}
    assert a == {'a': 'b'}


def test_mutability_merge_b():
    b = {'a': 'c'}
    assert s.dicts.merge({'a': 'b'}, b) == {'a': 'c'}
    assert b == {'a': 'c'}


def test_simple_merge():
    assert s.dicts.merge({'a': 'b'},
                         {'a': 'c', 'b': 'd'}) == {'a': 'c', 'b': 'd'}


def test_iterables_concatted():
    assert s.dicts.merge({'a': ('a', 'b')},
                         {'a': ('c', 'd')}, concat=True) == {'a': ('a', 'b', 'c', 'd')}


def test_iterables_not_concatted():
    assert s.dicts.merge({'a': ('a', 'b')},
                         {'a': ('c', 'd')}) == {'a': ('c', 'd')}


def test__concatable():
    assert s.dicts._concatable([], [])
    assert s.dicts._concatable((), ())
    assert not s.dicts._concatable((), [])
    assert not s.dicts._concatable([], 'a')


def test_only():
    assert s.dicts.take({'a': True, 'b': True, 'c': True}, ['a', 'b']) == {'a': True, 'b': True}


def test_padded_only():
    assert s.dicts.take({'a': True}, ['a', 'b', 'c'], padded=None) == {'a': True, 'b': None, 'c': None}


def test_drop():
    assert s.dicts.drop({'a': 'a', 'b': 'b'}, 'a') == {'b': 'b'}
    assert s.dicts.drop({'a': 'a', 'b': 'b'}, ['a', 'b']) == {}


def test__ks():
    assert s.dicts._ks(['a', 'b']) == ('a', 'b')
    assert s.dicts._ks('a') == ('a',)


def test_new():
    x, y = 'a', 'b'
    assert s.dicts.new(locals(), 'x', 'y') == {'x': 'a', 'y': 'b'}


def test_map():
    fn = lambda k, v: ['{}!!'.format(k), v]
    assert s.dicts.map(fn, {'a': {'b': [1, 2]}}) == {'a!!': {'b!!': [1, 2]}}


def test_to_nested():
    assert s.dicts.to_nested({'a.b': 'c'}) == {'a': {'b': 'c'}}


def test_to_dotted():
    assert s.dicts.to_dotted({'a': {'b': 'c'}}) == {'a.b': 'c'}
    with pytest.raises(AssertionError):
        s.dicts.to_dotted({'no.dots': {'or you': 'except'}})
    with pytest.raises(AssertionError):
        s.dicts.to_dotted({'no dots': {'or.you': 'except'}})
