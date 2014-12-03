import s


def test_actor_schema_matching():
    @s.async.actor
    def bob(self):
        while True:
            msg = yield self.recv()
            if s.schema.is_valid((':say_goodbye_to', str, str), msg):
                _, route, name = msg
                yield self.send(route, 'good bye: ' + name)
            elif s.schema.is_valid((':add_one', str, int), msg):
                _, route, x = msg
                yield self.send(route, x + 1)

    @s.async.actor
    def joe(self, route):
        bob_route = bob()
        yield self.send(bob_route, [':add_one', self(), 3])
        yield self.send(bob_route, [':say_goodbye_to', self(), 'joe'])
        msg1 = yield self.recv()
        msg2 = yield self.recv()
        yield s.sock.push(route, [msg1, msg2])

    @s.async.coroutine
    def main():
        route = s.sock.route()
        joe(route)
        with s.sock.bind('pull', route) as pull:
            msg = yield pull.recv()
            assert msg == [4, 'good bye: joe'], msg

    s.async.run_sync(main)


def test_actor():
    @s.async.actor
    def bob(self, route):
        while True:
            msg = yield self.recv()
            yield self.send(route, msg + '!')

    @s.async.actor
    def joe(self, route):
        bob_route = bob(self())
        for msg in ['hey', 'yo']:
            yield self.send(bob_route, msg)
            msg = yield self.recv()
            yield self.send(route, msg)

    @s.async.coroutine
    def main():
        route = s.sock.route()
        joe(route)
        with s.sock.bind('pull', route) as pull:
            msg = yield pull.recv()
            assert msg == 'hey!'
            msg = yield pull.recv()
            assert msg == 'yo!'

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


# [v() for k, v in globals().items() if k.startswith('test') and callable(v)]
