from __future__ import print_function, absolute_import
import s.async
from test_s.slow import flaky
import tornado.gen


@flaky
def test_coroutines_do_not_persist_between_runsync_calls():
    state = []
    @tornado.gen.coroutine
    def mutator():
        while True:
            state.append(None)
            yield tornado.gen.moment

    @tornado.gen.coroutine
    def one():
        mutator()
        yield tornado.gen.moment

    @tornado.gen.coroutine
    def two():
        yield tornado.gen.moment

    assert len(state) == 0
    s.async.run_sync(one)
    assert len(state) == 3
    s.async.run_sync(two)
    assert len(state) == 3
