import pytest
import s


def test_stack():
    start = s.fn._stack()
    @s.fn.logic
    def fn1():
        assert s.fn._stack() == ('logic:{}:fn1'.format(__name__),)
        return fn2()
    @s.fn.logic
    def fn2():
        assert s.fn._stack() == ('logic:{}:fn1'.format(__name__),
                                'logic:{}:fn2'.format(__name__))
        return True
    fn1()
    assert s.fn._stack() == start


def test_flow_in_logic():
    @s.fn.flow
    def flow():
        return True
    @s.fn.logic
    def logic():
        flow()
    with pytest.raises(AssertionError):
        logic()


def test_immutalize():
    val = {'a': 1}
    @s.fn.immutalize
    def fn2(x):
        x['a'] = 3
    with pytest.raises(ValueError):
        fn2(val)


def test_glue_in_logic():
    @s.fn.glue
    def glue():
        return True
    @s.fn.logic
    def logic():
        return glue()
    with pytest.raises(AssertionError):
        logic()


def f(x, *a):
    return x + 1
def g(x):
    return x * 2
def h(x):
    return 3 - x
def f2(x, y):
    return x - y
def g2(x, y):
    return x * y


def test_inline():
    assert s.fn.inline(f, g, h)(1) == -1
    assert s.fn.inline(f, g, h)(1) == h(g(f(1)))
    assert s.fn.inline(h, g, f)(1) == 5
    assert s.fn.inline(h, g, f)(1) == f(g(h(1)))


def test_inline_noncallable():
    with pytest.raises(AssertionError):
        s.fn.inline(h, g, 1)(1)


def test_thrush():
    assert s.fn.thrush(1, f, g, h) == -1


def test_thread_noncallable():
    with pytest.raises(AssertionError):
        s.fn.thrush(1, f, g, 2)


def test_logic_generator():
    @s.fn.logic
    def logic():
        for x in range(3):
            assert s.fn._stack() == ('logic:test_s.fast.fn:logic',)
            yield x
    for i, x in enumerate(logic()):
        assert i == x
        assert s.fn._stack() == ()


def test_logic_raise():
    @s.fn.logic
    def logic():
        1 / 0
    with pytest.raises(ZeroDivisionError):
        logic()


def test_logic_gen_raise():
    @s.fn.logic
    def logic():
        for x in range(3):
            yield x
        1 / 0
    with pytest.raises(ZeroDivisionError):
        for i, x in enumerate(logic()):
            assert i == x
