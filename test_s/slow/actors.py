from __future__ import print_function, absolute_import
import s.actors
import s.schema
import s.async
import tornado.gen
from test_s.slow import flaky


@flaky
def test_actor_schema_matching():
    @s.actors.actor
    def bob(self):
        while True:
            msg = yield self.recv()
            if s.schema.is_valid((':say_goodbye_to', str, str), msg):
                _, route, name = msg
                yield self.send(route, 'good bye: ' + name)
            elif s.schema.is_valid((':add_one', str, int), msg):
                _, route, x = msg
                yield self.send(route, x + 1)

    @s.actors.actor
    def joe(self, route):
        bob_route = bob()
        yield self.send(bob_route, [':add_one', self(), 3])
        yield self.send(bob_route, [':say_goodbye_to', self(), 'joe'])
        msg1 = yield self.recv()
        msg2 = yield self.recv()
        yield self.send(route, [msg1, msg2])

    @tornado.gen.coroutine
    def main():
        route = s.sock.route()
        joe(route)
        with s.sock.bind('pull', route) as pull:
            msg = yield pull.recv()
            assert msg == [4, 'good bye: joe'], msg

    s.async.run_sync(main)


@flaky
def test_actor():
    @s.actors.actor
    def bob(self, route):
        while True:
            msg = yield self.recv()
            yield self.send(route, msg + '!')

    @s.actors.actor
    def joe(self, route):
        bob_route = bob(self())
        for msg in ['hey', 'yo']:
            yield self.send(bob_route, msg)
            msg = yield self.recv()
            yield self.send(route, msg)

    @tornado.gen.coroutine
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
    @s.actors.actor(selective_receive=True)
    def bob(self):
        state = 0
        while True:
            msg = yield self.recv()
            if state == 0:
                if s.schema.is_valid((':first_thing', str), msg):
                    _, route = msg
                    yield self.send(route, 'first')
                    state = 1
                    continue
            elif state == 1:
                if s.schema.is_valid((':second_thing', str), msg):
                    _, route = msg
                    yield self.send(route, 'second')
                    break
            self.requeue()

    @s.actors.actor
    def joe(self, route):
        bob_route = bob()
        yield self.send(bob_route, [':second_thing', self()])
        yield self.send(bob_route, [':first_thing', self()])
        msg1 = yield self.recv()
        msg2 = yield self.recv()
        yield self.send(route, [msg1, msg2])

    @tornado.gen.coroutine
    def main():
        route = s.sock.route()
        joe(route)
        with s.sock.bind('pull', route) as pull:
            msg = yield pull.recv()
            assert msg == ['first', 'second'], msg

    s.async.run_sync(main)
