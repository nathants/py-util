from __future__ import absolute_import, print_function
import threading


def new(fn, *a, **kw):
    daemon = kw.pop('_daemon', True)
    obj = threading.Thread(target=fn, args=a, kwargs=kw)
    obj.daemon = daemon
    obj.start()
    return obj
