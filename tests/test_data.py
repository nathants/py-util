import util.func
import util.data
import pytest
import mock
import tornado.concurrent


def test_future():
    f = tornado.concurrent.Future()
    f2 = util.data.freeze(f)
    val = [1, 2]
    f.set_result(val)
    val.append(3)
    assert f2.result() == [1, 2]


def test_unicode_synonymous_with_str():
    assert util.data.freeze({u'a': 'b'}) == {'a': 'b'}
    assert util.data.freeze(u'asdf') == 'asdf'


def test_setitem_freeze():
    with pytest.raises(Exception):
        util.data.freeze({'a': 1})['a'] = 2


def test_pop_freeze():
    with pytest.raises(Exception):
        util.data.freeze({'a': 1}).pop()


def test_popitem_freeze():
    with pytest.raises(Exception):
        util.data.freeze({'a': 1}).popitem()


def test_update_freeze():
    with pytest.raises(Exception):
        util.data.freeze({'a': 1}).update()


def test_clear_freeze():
    with pytest.raises(Exception):
        util.data.freeze({'a': 1}).clear()


def test_append_freeze():
    with pytest.raises(ValueError):
        util.data.freeze([]).append(1)


def test_getitem_freeze():
    assert 1 == util.data.freeze({'a': 1})['a']


def test_set_freeze():
    x = {1, 2, 3}
    y = util.data.freeze(x)
    x.add(4)
    assert y == {1, 2, 3}


def test_nested_freeze():
    x = {1}
    y = util.data.freeze({'val': x})
    x.add(2)
    assert len(y['val']) == 1


def test_list_freeze():
    x = [1, 2, 3]
    y = util.data.freeze(x)
    x.append(4)
    assert y == [1, 2, 3]


def test_dont_refreeze():
    fn = util.data.freeze
    with mock.patch.object(util.data, 'freeze') as m:
        m.side_effect = fn
        x = [1, 2, 3]
        assert m.call_count == 0
        x = util.data.freeze(x)
        assert m.call_count == 4 # called once for [] and once for each element
        util.data.freeze(x)
        assert m.call_count == 5 # called once for [] and shortcircuit
        util.data.freeze(x)
        assert m.call_count == 6 # called once for [] and shortcircuit


def test_equality():
    assert util.data.freeze([1, 2]) == [1, 2]
    assert util.data.freeze((1, 2)) == (1, 2)
    assert not util.data.freeze([1, 2]) == (x for x in range(1, 3))
