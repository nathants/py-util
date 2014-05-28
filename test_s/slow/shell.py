import s
import os
import sys


_keys = list(sys.modules.keys())


def setup_function(fn):
    fn.ctx = s.shell.tempdir()
    fn.ctx.__enter__()
    for k, v in list(sys.modules.items()):
        if k not in _keys:
            del sys.modules[k]
    sys.path.insert(0, os.getcwd())


def teardown_function(fn):
    fn.ctx.__exit__(None, None, None)
    sys.path.pop(0)


def test_module_name():
    s.shell.run('mkdir -p a/b/c')
    s.shell.run('touch a/b/__init__.py a/b/c/__init__.py a/b/c/foo.py')
    assert 'b.c.foo' == s.shell.module_name(os.path.abspath('a/b/c/foo.py'))


s.hacks.decorate(globals(), __name__, s.fn.badfunc)
