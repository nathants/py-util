import s.actors
import s.schema
import toro
import tornado.gen


def test_actor():
    @s.actors.actor(ipc=False)
    def bob(self, route):
        while True:
            msg = yield self.recv()
            yield self.send(route, msg + '!')

    @s.actors.actor(ipc=False)
    def joe(self, route):
        bob_route = bob(self())
        for msg in ['hey', 'yo']:
            yield self.send(bob_route, msg)
            msg = yield self.recv()
            yield self.send(route, msg)

    @tornado.gen.coroutine
    def main():
        route = toro.Queue()
        joe(route)
        msg = yield route.get()
        assert msg == 'hey!'
        msg = yield route.get()
        assert msg == 'yo!'

    s.async.run_sync(main)


def test_actor_selective_receive():
    @s.actors.actor(selective_receive=True, ipc=False)
    def bob(self):
        state = 0
        while True:
            msg = yield self.recv()
            if state == 0:
                if s.schema.is_valid((':first_thing', object), msg):
                    _, route = msg
                    yield self.send(route, 'first')
                    state = 1
                    continue
            elif state == 1:
                if s.schema.is_valid((':second_thing', object), msg):
                    _, route = msg
                    yield self.send(route, 'second')
                    break
            self.requeue()

    @s.actors.actor(ipc=False)
    def joe(self, route):
        bob_route = bob()
        yield self.send(bob_route, [':second_thing', self()])
        yield self.send(bob_route, [':first_thing', self()])
        msg1 = yield self.recv()
        msg2 = yield self.recv()
        yield self.send(route, [msg1, msg2])

    @tornado.gen.coroutine
    def main():
        route = toro.Queue()
        joe(route)
        msg = yield route.get()
        assert msg == ['first', 'second'], msg

    s.async.run_sync(main)
