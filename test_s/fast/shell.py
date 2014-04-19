import s
import pytest


def test_echo():
    assert 'asdf' == s.shell.run('echo asdf')


def test_exitcode():
    assert 1 == s.shell.run('false', warn=True).exitcode


def test_excepts():
    with pytest.raises(Exception):
        s.shell.run('false')


def test_interactive():
    s.shell.run('true', interactive=True)
    s.shell.run('false', interactive=True, warn=True)

def test_interactive_excepts():
    with pytest.raises(Exception):
        s.shell.run('false', interactive=True)


def test_callback():
    val = []
    cb = lambda x: val.append(x)
    s.shell.run('echo asdf', callback=cb)
    assert val == ['asdf']
