from __future__ import print_function, absolute_import
import s.func


def _plus_one(x):
    return x + 1


def _times_two(x):
    return x * 2


def _three_minus(x):
    return 3 - x


def _subtract(x, y):
    return x - y


def _divide(x, y):
    try:
        return x / y
    except:
        return None


def test_name():
    assert s.func.name(test_name) == 'test_s.fast.func:test_name'


def test_pipe_first():
    assert s.func.pipe(1, [_subtract, 3], _plus_one) == -1


def test_pipe_last():
    assert s.func.pipe_last(1, [_subtract, 3], _plus_one) == 3


def test_pipe_some():
    assert s.func.pipe_some(1, [_divide, 0]) is None


def test_pipe_some_last():
    assert s.func.pipe_some_last(0, [_divide, 1]) is None


def test_module_name():
    assert s.func.module_name(test_module_name) == 'test_s.fast.func'
