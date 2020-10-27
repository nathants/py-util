import util.dicts
import pytest
import operator

def test_update_in():
    assert util.dicts.update_in({'a': {'b': 'c', 'd': 'e'}}, ['a', 'b'], operator.add, '!') == {'a': {'b': 'c!', 'd': 'e'}}
    assert util.dicts.update_in({'a': {'b': 'c'}}, 'a', str) == {'a': "{'b': 'c'}"}
    assert util.dicts.update_in({}, 'a', str) == {'a': '{}'}

def test_get():
    assert util.dicts.get({'a': {'b': 'c'}}, ['a', 'b']) == 'c'

def test_set():
    assert util.dicts.set({}, ['a', 'b', 'c'], 'asdf') == {'a': {'b': {'c': 'asdf'}}}
    assert util.dicts.set({'e': 'f'}, ['a', 'b'], 'c') == {'a': {'b': 'c'}, 'e': 'f'}
    assert util.dicts.set({'a': {'d': 'e', 'b': 'c'}}, ['a', 'b'], 'c!') == {'a': {'d': 'e', 'b': 'c!'}}

def test_set_subset():
    assert util.dicts.set({'a': {'b': 'c', 'd': 'e'}}, 'a', {'b': 'c'}) == {'a': {'b': 'c'}}

def test_merge_freezes():
    assert util.dicts.merge({'a': 'b'}, {'a': ['c', 'd']}) == {'a': ['c', 'd']}

def test_merge():
    assert util.dicts.merge({'a': {'b': 'c'}},
                            {'a': {'d': 'e'}}) == {'a': {'b': 'c',
                                                   'd': 'e'}}

def test_merge_dict_with_nondict():
    assert util.dicts.merge({'a': 'b'}, {'a': {'b': 'c'}}) == {'a': {'b': 'c'}}

def test_mutability_merge_a():
    a = {'a': 'b'}
    assert util.dicts.merge(a, {'a': 'c'}) == {'a': 'c'}
    assert a == {'a': 'b'}

def test_mutability_merge_b():
    b = {'a': 'c'}
    assert util.dicts.merge({'a': 'b'}, b) == {'a': 'c'}
    assert b == {'a': 'c'}

def test_simple_merge():
    assert util.dicts.merge({'a': 'b'},
                            {'a': 'c', 'b': 'd'}) == {'a': 'c', 'b': 'd'}

def test_iterables_concatted():
    assert util.dicts.merge({'a': ('a', 'b')},
                            {'a': ('c', 'd')}, concat=True) == {'a': ('a', 'b', 'c', 'd')}

def test_iterables_not_concatted():
    assert util.dicts.merge({'a': ('a', 'b')},
                            {'a': ('c', 'd')}) == {'a': ('c', 'd')}

def test__concatable():
    assert util.dicts._concatable([], [])
    assert util.dicts._concatable((), ())
    assert not util.dicts._concatable((), [])
    assert not util.dicts._concatable([], 'a')

def test_only():
    assert util.dicts.take({'a': True, 'b': True, 'c': True}, ['a', 'b']) == {'a': True, 'b': True}

def test_padded_only():
    assert util.dicts.take({'a': True}, ['a', 'b', 'c'], padded=None) == {'a': True, 'b': None, 'c': None}

def test_drop():
    assert util.dicts.drop({'a': 'a', 'b': 'b'}, 'a') == {'b': 'b'}
    assert util.dicts.drop({'a': 'a', 'b': 'b'}, ['a', 'b']) == {}

def test_drop_in():
    assert util.dicts.drop_in({'a': 'b'}, ['c', 'd']) == {'a': 'b'}
    assert util.dicts.drop_in({'a': {'b': 'c', 'd': 'e'}}, ['a']) == {}
    assert util.dicts.drop_in({'a': {'b': 'c', 'd': 'e'}}, ['a', 'b']) == {'a': {'d': 'e'}}

def test__ks():
    assert util.dicts._ks(['a', 'b']) == ('a', 'b')
    assert util.dicts._ks('a') == ('a',)

def test_new():
    x, y = 'a', 'b'
    assert util.dicts.new(locals(), 'x', 'y') == {'x': 'a', 'y': 'b'}

def test_map():
    fn = lambda k, v: ['{}!!'.format(k), v]
    assert util.dicts.map(fn, {'a': {'b': [1, 2]}}) == {'a!!': {'b!!': [1, 2]}}

def test_to_nested():
    assert util.dicts.to_nested({'a.b': 'c'}) == {'a': {'b': 'c'}}

def test_to_dotted():
    assert util.dicts.to_dotted({'a': {'b': 'c'}}) == {'a.b': 'c'}
    with pytest.raises(AssertionError):
        util.dicts.to_dotted({'no.dots': {'or you': 'except'}})
    with pytest.raises(AssertionError):
        util.dicts.to_dotted({'no dots': {'or.you': 'except'}})
