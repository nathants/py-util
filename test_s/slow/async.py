from __future__ import print_function, absolute_import
import s
from test_s.slow import flaky


@flaky
def test_actor_schema_matching():
    @s.async.actor
    def bob(self):
        while True:
            msg = yield self.recv()
            if s.schema.is_valid((':say_goodbye_to', str, str), msg):
                _, route, name = msg
                yield s.sock.push(route, 'good bye: ' + name)
            elif s.schema.is_valid((':add_one', str, int), msg):
                _, route, x = msg
                yield s.sock.push(route, x + 1)

    @s.async.actor
    def joe(self, route):
        bob_route = bob()
        yield s.sock.push(bob_route, [':add_one', self(), 3])
        yield s.sock.push(bob_route, [':say_goodbye_to', self(), 'joe'])
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


@flaky
def test_actor():
    @s.async.actor
    def bob(self, route):
        while True:
            msg = yield self.recv()
            yield s.sock.push(route, msg + '!')

    @s.async.actor
    def joe(self, route):
        bob_route = bob(self())
        for msg in ['hey', 'yo']:
            yield s.sock.push(bob_route, msg)
            msg = yield self.recv()
            yield s.sock.push(route, msg)

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


@flaky
def test_actor_selective_receive():
    @s.async.actor(selective_receive=True)
    def bob(self):
        state = 0
        while True:
            msg = yield self.recv()
            if state == 0:
                if s.schema.is_valid((':first_thing', str), msg):
                    _, route = msg
                    yield s.sock.push(route, 'first')
                    state = 1
                    continue
            elif state == 1:
                if s.schema.is_valid((':second_thing', str), msg):
                    _, route = msg
                    yield s.sock.push(route, 'second')
                    break
            self.requeue()

    @s.async.actor
    def joe(self, route):
        bob_route = bob()
        yield s.sock.push(bob_route, [':second_thing', self()])
        yield s.sock.push(bob_route, [':first_thing', self()])
        msg1 = yield self.recv()
        msg2 = yield self.recv()
        yield s.sock.push(route, [msg1, msg2])

    @s.async.coroutine
    def main():
        route = s.sock.route()
        joe(route)
        with s.sock.bind('pull', route) as pull:
            msg = yield pull.recv()
            assert msg == ['first', 'second'], msg

    s.async.run_sync(main)
