import pytest
import s


def test_immutalizes_logic():
    @s.func.logic
    def fn(x):
        x[1] = 2
    with pytest.raises(ValueError):
        fn({})


def test__stack():
    start = s.func._stack()
    @s.func.logic
    def fn1():
        assert s.func._stack() == ('logic:{}:fn1'.format(__name__),)
        return fn2()
    @s.func.logic
    def fn2():
        assert s.func._stack() == ('logic:{}:fn1'.format(__name__),
                                   'logic:{}:fn2'.format(__name__))
        return True
    fn1()
    assert s.func._stack() == start


def test_flow_in_logic():
    @s.func.flow
    def flow():
        return True
    @s.func.logic
    def logic():
        flow()
    with pytest.raises(AssertionError):
        logic()


def test__immutalize():
    val = {'a': 1}
    @s.func._immutalize
    def fn2(x):
        x['a'] = 3
    with pytest.raises(ValueError):
        fn2(val)


def test_glue_in_logic():
    @s.func.glue
    def glue():
        return True
    @s.func.logic
    def logic():
        return glue()
    with pytest.raises(AssertionError):
        logic()


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


def test_thread_noncallable():
    with pytest.raises(AssertionError):
        s.func.pipe(1, _plus_one, _times_two, 2)


def test_logic_generator():
    @s.func.logic
    def logic():
        for x in range(3):
            assert s.func._stack() == ('logic:test_s.fast.func:logic',)
            yield x
    for i, x in enumerate(logic()):
        assert i == x
        assert s.func._stack() == ()


def test_logic_raise():
    @s.func.logic
    def logic():
        1 / 0
    with pytest.raises(ZeroDivisionError):
        logic()


def test_logic_gen_raise():
    @s.func.logic
    def logic():
        for x in range(3):
            yield x
        1 / 0
    with pytest.raises(ZeroDivisionError):
        for i, x in enumerate(logic()):
            assert i == x
