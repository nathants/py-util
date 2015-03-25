from __future__ import print_function, absolute_import
import tornado
import tornado.gen
import tornado.ioloop


# TODO is this behavior needed? callback poping?
def run_sync(fn, *a, **kw):
    timeout = kw.pop('timeout', None)
    tornado.ioloop.IOLoop.clear_instance()
    io = tornado.ioloop.IOLoop.instance()
    val = io.run_sync(lambda: fn(*a, **kw), timeout=timeout)
    while io._callbacks:
        io._callbacks.pop()
    return val


# TODO is this actually good? obfuscates?
def make_sync(fn):
    def fn_sync(*a, **kw):
        @tornado.gen.coroutine
        def main():
            val = yield fn(*a, **kw)
            raise tornado.gen.Return(val)
        return run_sync(main)
    return fn_sync
