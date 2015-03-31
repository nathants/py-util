from __future__ import print_function, absolute_import
import pytest
import s.cached


def test_methods_are_illegal():
    class Foo(object):
        @s.cached.disk
        def fn():
            pass
    with pytest.raises(AssertionError):
        Foo().fn()


def test_disk():
    state = {'val': 0}
    @s.cached.disk
    def fn():
        state['val'] += 1
    fn.clear_cache()
    fn(), fn(), fn()
    assert state['val'] == 1
