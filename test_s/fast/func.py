import pytest
import collections
import s


def _plus_one(x, *a):
    return x + 1


def _times_two(x):
    return x * 2


def _three_minus(x):
    return 3 - x


def test_inline():
    assert s.func.inline(_plus_one, _times_two, _three_minus)(1) == -1
    assert s.func.inline(_plus_one, _times_two, _three_minus)(1) == _three_minus(_times_two(_plus_one(1)))
    assert s.func.inline(_three_minus, _times_two, _plus_one)(1) == 5
    assert s.func.inline(_three_minus, _times_two, _plus_one)(1) == _plus_one(_times_two(_three_minus(1)))


def test_inline_noncallable():
    with pytest.raises(AssertionError):
        s.func.inline(_three_minus, _times_two, 1)(1)


def test_pipe():
    assert s.func.pipe(1, _plus_one, _times_two, _three_minus) == -1


def test_pipe_noncallable():
    with pytest.raises(AssertionError):
        s.func.pipe(1, _plus_one, _times_two, 2)


def test_name():
    assert s.func.name(test_name) == 'test_s.fast.func:test_name'
