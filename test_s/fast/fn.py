import pytest
import s
import logging


def setup_module():
    s.log.setup(level='debug', short=True)


def test1():
    start = s.fn.stack()
    @s.fn.logic
    def fn1():
        assert s.fn.stack()[-1:] == (('logic', '{}:fn1()'.format(__name__)),)
        return fn2()
    @s.fn.logic
    def fn2():
        assert s.fn.stack()[-2:] == (('logic', '{}:fn1()'.format(__name__)),
                                     ('logic', '{}:fn2()'.format(__name__)))
        return True
    fn1()
    assert s.fn.stack() == start


def test_flow_in_logic():
    @s.fn.logic
    def fn1():
        return fn2()
    @s.fn.flow
    def fn2():
        return True
    with pytest.raises(AssertionError):
        fn1()


def test0():
    val = {'a': 1}
    def fn1(x):
        x['a'] = 2
    fn1(val)
    assert val['a'] == 2
    @s.fn.immutalize
    def fn2(x):
        x['a'] = 3
    with pytest.raises(ValueError):
        fn2(val)
    assert val['a'] == 2



def test2():
    @s.fn.logic
    def fn1():
        return True
    fn1()
    fn1()

def test_glue_in_logic():
    @s.fn.logic
    def fn1():
        return fn2()
    @s.fn.glue
    def fn2():
        return True
    with pytest.raises(AssertionError):
        fn1()


def f(x, *a):
    return x + 1
def g(x):
    return x * 2
def h(x):
    return x + 3
def f2(x, y):
    return x - y
def g2(x, y):
    return x * y


def test_inline():
    assert s.fn.inline(f, g, h)(1) == 7
    assert s.fn.inline(f, g, h)(1) == h(g(f(1)))
    assert s.fn.inline(h, g, f)(1) == 9
    assert s.fn.inline(h, g, f)(1) == f(g(h(1)))


def test_inline_noncallable():
    with pytest.raises(AssertionError):
        s.fn.inline(h, g, 1)(1)


def test_thread():
    assert s.fn.thread(1, f, g, h) == 7


def test_thread_noncallable():
    with pytest.raises(AssertionError):
        s.fn.thread(1, f, g, 2)
