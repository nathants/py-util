import s
import pytest


def test_get():
    assert s.dicts.get({1: {2: 3}}, 1, 2) == 3


def test_put():
    assert s.dicts.put({}, 3, 1, 2) == {1: {2: 3}}


def test_merge_freezes():
    assert s.dicts.merge({1: 2}, {1: [3, 4]}) == {1: (3, 4)}


def test_merge():
    assert s.dicts.merge({1: {2: 3}},
                         {1: {4: 5}}) == {1: {2: 3,
                                              4: 5}}


def test_merge_dict_with_nondict():
    assert s.dicts.merge({1: 2}, {1: {2: 3}}) == {1: {2: 3}}


def test_mutability_merge_a():
    a = {1: 2}
    assert s.dicts.merge(a, {1: 3}) == {1: 3}
    assert a == {1: 2}


def test_mutability_merge_b():
    b = {1: 3}
    assert s.dicts.merge({1: 2}, b) == {1: 3}
    assert b == {1: 3}


def test_simple_merge():
    assert s.dicts.merge({1: 2},
                         {1: 3, 2: 4}) == {1: 3, 2: 4}


def test_iterables_concatted():
    assert s.dicts.merge({1: {2: (1, 2)}},
                         {1: {2: (3, 4)}}, concat=True) == {1: {2: (1, 2, 3, 4)}}


def test__concatable():
    assert s.dicts._concatable([], [])
    assert s.dicts._concatable((), ())
    assert not s.dicts._concatable((), [])
    assert not s.dicts._concatable([], 1)


def test_only():
    assert s.dicts.take({1: True, 2: True, 3: True}, 1, 2) == {1: True, 2: True}


def test_padded_only():
    assert s.dicts.take({1: True}, 1, 2, 3, padded=None) == {1: True, 2: None, 3: None}


def test_drop():
    assert s.dicts.drop({1: 1, 2: 2}, 1) == {2: 2}


def test__ks():
    assert s.dicts._ks([1, 2]) == (1, 2)
    assert s.dicts._ks((1, 2)) == (1, 2)
    with pytest.raises(TypeError):
        s.dicts._ks(None)


def test_new():
    x, y = 1, 2
    assert s.dicts.new(locals(), 'x', 'y') == {'x': 1, 'y': 2}


def test_map():
    fn = lambda k, v: ['{}!!'.format(k), v]
    assert s.dicts.map(fn, {1: {2: 3}}) == {'1!!': {'2!!': 3}}
