import s
import pytest


def test_setitem():
    with pytest.raises(ValueError):
        s.data.immutalize({'a': 1})['a'] = 2


def test_getitem():
    assert 1 == s.data.immutalize({'a': 1})['a']


def test_immutalize_set():
    x = {1, 2, 3}
    y = s.data.immutalize(x)
    x.add(4)
    assert y == {1, 2, 3}


def test_immutalize_nested():
    x = {1}
    y = s.data.immutalize({'val': x})
    x.add(2)
    assert len(y['val']) == 1


def test_immutalize_list():
    x = [1, 2, 3]
    y = s.data.immutalize(x)
    x.append(4)
    assert y == (1, 2, 3)
