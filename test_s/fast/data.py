import s
import pytest
import mock


def test_setitem_immutalize():
    with pytest.raises(Exception):
        s.data.immutalize({'a': 1})['a'] = 2


def test_pop_immutalize():
    with pytest.raises(Exception):
        s.data.immutalize({'a': 1}).pop()


def test_popitem_immutalize():
    with pytest.raises(Exception):
        s.data.immutalize({'a': 1}).popitem()


def test_update_immutalize():
    with pytest.raises(Exception):
        s.data.immutalize({'a': 1}).update()


def test_clear_immutalize():
    with pytest.raises(Exception):
        s.data.immutalize({'a': 1}).clear()


def test_append_immutalize():
    with pytest.raises(AttributeError):
        s.data.immutalize([]).append(1)


def test_getitem_immutalize():
    assert 1 == s.data.immutalize({'a': 1})['a']


def test_set_immutalize():
    x = {1, 2, 3}
    y = s.data.immutalize(x)
    x.add(4)
    assert y == {1, 2, 3}


def test_nested_immutalize():
    x = {1}
    y = s.data.immutalize({'val': x})
    x.add(2)
    assert len(y['val']) == 1


def test_list_immutalize():
    x = [1, 2, 3]
    y = s.data.immutalize(x)
    x.append(4)
    assert y == (1, 2, 3)


def test_dont_reimmutalize():
    fn = s.data.immutalize
    with mock.patch.object(s.data, 'immutalize') as m:
        m.side_effect = fn
        x = [1, 2, 3]
        assert m.call_count == 0
        x = s.data.immutalize(x)
        assert m.call_count == 4 # called once for [] and once for each element
        s.data.immutalize(x)
        assert m.call_count == 5 # called once for [] and shortcircuit
        s.data.immutalize(x)
        assert m.call_count == 6 # called once for [] and shortcircuit
