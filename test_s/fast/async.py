import s


def test_actor():
    @s.async.actor
    def bob(self, route):
        msg = yield self.recv()
        yield self.send(route, msg + '!')
    @s.async.actor
    def joe(self, route):
        bob_route = bob(self())
        yield self.send(bob_route, 'hey')
        msg = yield self.recv()
        yield self.send(route, msg)
    @s.async.coroutine
    def main():
        route = s.sock.route()
        joe(route)
        with s.sock.bind('pull', route) as pull:
            msg = yield pull.recv()
        assert msg == 'hey!'
    s.async.run_sync(main)


def test_coroutines_do_not_persist_between_runsync_calls():
    state = []
    @s.async.coroutine
    def mutator():
        while True:
            state.append(None)
            yield s.async.moment
    @s.async.coroutine
    def one():
        mutator()
        yield s.async.moment
    @s.async.coroutine
    def two():
        yield s.async.moment
    assert len(state) == 0
    s.async.run_sync(one)
    assert len(state) == 3
    s.async.run_sync(two)
    assert len(state) == 3


def test_coroutine_return():
    @s.async.coroutine
    def fn():
        yield s.async.moment
        raise s.async.Return(123)
    assert s.async.run_sync(fn) == 123


def test_coroutine():
    state = []
    @s.async.coroutine
    def zero():
        for i in range(2):
            state.append(i)
            yield s.async.moment
    @s.async.coroutine
    def ten():
        zero()
        for i in range(10, 12):
            state.append(i)
            yield s.async.moment
    s.async.run_sync(ten)
    assert state == [0, 10, 1, 11]
