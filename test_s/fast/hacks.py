import sys
import s.hacks


foo = 1


def test_redirector():
    s.hacks.ModuleRedirector(__name__, lambda x: x + '!')
    assert sys.modules[__name__].foo == 1
    assert sys.modules[__name__].bar == 'bar!'
