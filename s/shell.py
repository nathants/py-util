import subprocess
import os

_state = {}


def _set_state(key):
    @contextlib.contextmanager
    def fn():
        orig = _state.get(key)
        _state[key] = True
        try:
            yield
        except:
            raise
        finally:
            del _state[key]
            if orig is not None:
                _state[key] = orig
    return fn


set_stream = _set_state('stream')


def run(stream=False, *a):
    stream = _state.get('stream', stream)
    cmd = ' '.join(a)
    1/0


def listdir(path='.', absolute=False):
    return list_filtered(path, absolute, lambda *a: True)


def dirs(path='.', absolute=False):
    return list_filtered(path, absolute, os.path.isdir)


def files(path='.', absolute=False):
    return list_filtered(path, absolute, os.path.isfile)


def list_filtered(path, absolute, predicate):
    path = os.path.expanduser(path)
    resolve = lambda x: os.path.abspath(os.path.join(path, x))
    return [resolve(x) if absolute else x
            for x in sorted(os.listdir(path))
            if predicate(os.path.join(path, x))]
