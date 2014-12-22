from __future__ import print_function, absolute_import
import pytest
import s
import s.sock


def test_cannot_use_none_as_message():
    @s.async.coroutine
    def main():
        yield s.sock.push(s.sock.route(), None)
    with pytest.raises(AssertionError):
        s.async.run_sync(main)


def test_pub_sub():
    route = s.sock.route()
    state = {'send': True}
    @s.async.coroutine
    def pubber():
        with s.sock.bind('pub', route) as pub:
            while state['send']:
                yield pub.send('asdf')
                yield s.async.sleep(.001)
    @s.async.coroutine
    def subber():
        pubber()
        with s.sock.connect('sub', route) as sock:
            topic, msg = yield sock.recv()
        assert msg == 'asdf'
    s.async.run_sync(subber)
    state['send'] = False


def test_push_pull_reversed_connect_bind():
    route = s.sock.route()
    @s.async.coroutine
    def pusher():
        with s.sock.bind('push', route) as sock:
            yield sock.send('asdf')
    @s.async.coroutine
    def puller():
        pusher()
        msg = yield s.sock.pull(route)
        assert msg == 'asdf'
    s.async.run_sync(puller)


def test_push_pull_tcp():
    route = 'tcp://0.0.0.0:{}'.format(s.net.free_port())
    @s.async.coroutine
    def pusher():
        yield s.sock.push(route, 'asdf')
    @s.async.coroutine
    def puller():
        pusher()
        with s.sock.bind('pull', route) as sock:
            val = yield sock.recv()
            assert val == 'asdf'
    s.async.run_sync(puller)


def test_push_pull():
    route = s.sock.route()
    @s.async.coroutine
    def pusher():
        yield s.sock.push(route, 'asdf')
    @s.async.coroutine
    def puller():
        pusher()
        with s.sock.bind('pull', route) as sock:
            val = yield sock.recv()
            assert val == 'asdf'
    s.async.run_sync(puller)


def test_async_methods_error_when_no_ioloop():
    s.async.ioloop().clear()
    with pytest.raises(AssertionError):
        s.sock.bind('pull', s.sock.route()).recv()
    with pytest.raises(AssertionError):
        s.sock.bind('pull', s.sock.route()).send('')


def test_timeout():
    @s.async.coroutine
    def main():
        with s.time.timer() as t:
            with s.sock.timeout(.1) as sock:
                val = yield sock.recv()
                assert val == ''
        assert t['seconds'] >= .1
    s.async.run_sync(main)


def test_select():
    r1 = s.sock.route()
    r2 = s.sock.route()
    @s.async.coroutine
    def pusher(route, msg, seconds=0):
        yield s.async.sleep(seconds)
        yield s.sock.push(route, msg)
    @s.async.coroutine
    def main():
        pusher(r1, 'msg1')
        pusher(r2, 'msg2', .1)
        with s.sock.bind('pull', r1) as p1, s.sock.bind('pull', r2) as p2, s.sock.timeout(.2) as t:
            sock, msg = yield s.sock.select(p1, p2, t)
            assert msg == 'msg1' and sock == id(p1)
            sock, msg = yield s.sock.select(p1, p2, t)
            assert msg == 'msg2' and sock == id(p2)
            sock, msg = yield s.sock.select(p1, p2, t)
            assert sock == id(t) and msg == ''
    s.async.run_sync(main)


def test_push_pull_device_middleware():
    r1 = s.sock.route()
    r2 = s.sock.route()
    @s.async.coroutine
    def pusher():
        yield s.sock.push(r1, 'job1')
    @s.async.coroutine
    def streamer():
        with s.sock.bind('pull', r1) as puller, s.sock.bind('push', r2) as pusher:
            msg = yield puller.recv()
            yield pusher.send(msg + ' [streamer]')
    @s.async.coroutine
    def main():
        pusher()
        streamer()
        msg = yield s.sock.pull(r2)
        assert msg == 'job1 [streamer]'
    s.async.run_sync(main)


def test_push_pull_data():
    route = s.sock.route()
    @s.async.coroutine
    def pusher():
        with s.sock.bind('push', route) as sock:
            yield sock.send({'a': '123'})
    @s.async.coroutine
    def puller():
        pusher()
        msg = yield s.sock.pull(route)
        assert msg == {'a': '123'}
    s.async.run_sync(puller)


def test_req_rep():
    route = s.sock.route()
    @s.async.coroutine
    def requestor():
        with s.sock.bind('req', route) as req:
            yield req.send('asdf')
            msg = yield req.recv()
            assert msg == 'asdf!!'
    @s.async.coroutine
    def replier():
        requestor()
        with s.sock.connect('rep', route) as rep:
            msg = yield rep.recv()
            yield rep.send(msg + '!!')
    s.async.run_sync(replier)


def test_pub_sub_subscriptions():
    route = s.sock.route()
    state = {'send': True}
    @s.async.coroutine
    def pubber():
        yield s.async.sleep(.01)
        with s.sock.bind('pub', route) as pub:
            while state['send']:
                yield pub.send('asdf', topic='a')
                yield pub.send('123', topic='b')
                yield s.async.sleep(.001)
    @s.async.coroutine
    def subber():
        pubber()
        with s.sock.connect('sub', route) as sock1:
            responses = set()
            for _ in range(2):
                msg = yield sock1.recv()
                responses.add(msg)
            assert responses == {('a', 'asdf'), ('b', '123')}
        with s.sock.connect('sub', route, subscriptions=['a']) as sock2:
            responses = set()
            for _ in range(2):
                msg = yield sock2.recv()
                responses.add(msg)
            assert responses == {('a', 'asdf')}
        state['send'] = False
    s.async.run_sync(subber)


def test_req_rep_device():
    r1 = s.sock.route()
    r2 = s.sock.route()
    @s.async.coroutine
    def replier(x):
        with s.sock.connect('rep', r2) as rep:
            msg = yield rep.recv()
            yield rep.send('thanks for: {msg}, from rep{x}'.format(**locals()))
    @s.async.coroutine
    def main():
        replier(1)
        replier(2)
        with s.sock.connect('req', r1) as req:
            responses = set()
            for _ in range(2):
                yield req.send('asdf')
                msg = yield req.recv()
                responses.add(msg)
            assert responses == {'thanks for: asdf, from rep1',
                                 'thanks for: asdf, from rep2'}
    proc = s.proc.new(s.sock.device, 'QUEUE', r1, r2)
    s.async.run_sync(main)
    proc.terminate()


def test_req_rep_device_middleware():
    r1 = s.sock.route()
    r2 = s.sock.route()
    @s.async.coroutine
    def replier():
        with s.sock.connect('rep', r2) as rep:
            msg = yield rep.recv()
            yield rep.send('thanks for: ' + msg)
    @s.async.coroutine
    def queue():
        yield s.async.moment
        router = s.sock.bind('router', r1).__enter__()
        dealer = s.sock.bind('dealer', r2).__enter__()
        @s.async.coroutine
        def route():
            while True:
                msg = yield router.recv()
                msg = msg[:-1] + (msg[-1] + ' [routed]',)
                dealer.send(msg)
        @s.async.coroutine
        def deal():
            while True:
                msg = yield dealer.recv()
                msg = msg[:-1] + (msg[-1] + ' [dealt]',)
                router.send(msg)
        route()
        deal()
    @s.async.coroutine
    def main():
        queue()
        replier()
        with s.sock.connect('req', r1) as req:
            yield req.send('asdf')
            msg = yield req.recv()
            assert msg == 'thanks for: asdf [routed] [dealt]'
    s.async.run_sync(main)


def test_pub_sub_device():
    r1 = s.sock.route()
    r2 = s.sock.route()
    state = {'send': True}
    @s.async.coroutine
    def pubber(x):
        with s.sock.connect('pub', r1) as pub:
            while state['send']:
                yield pub.send('asdf', topic='topic{}'.format(x))
                yield s.async.sleep(.01)
    @s.async.coroutine
    def main():
        pubber(1)
        pubber(2)
        responses = set()
        with s.sock.connect('sub', r2) as sub:
            for _ in range(100):
                msg = yield sub.recv()
                responses.add(msg)
        assert responses == {('topic1', 'asdf'),
                             ('topic2', 'asdf')}
    proc = s.proc.new(s.sock.device, 'forwarder', r1, r2)
    s.async.run_sync(main)
    state['send'] = False
    proc.terminate()


def test_pub_sub_device_middleware():
    r1 = s.sock.route()
    r2 = s.sock.route()
    state = {'send': True}
    @s.async.coroutine
    def pubber():
        with s.sock.connect('pub', r1) as pub:
            while state['send']:
                yield pub.send('asdf', topic='topic1')
                yield s.async.sleep(.01)
    @s.async.coroutine
    def forwarder():
        with s.sock.bind('sub', r1) as sub, s.sock.bind('pub', r2) as pub:
            while True:
                topic, msg = yield sub.recv()
                msg += ' [sub.on_recv]'
                yield pub.send(msg, topic=topic)
    @s.async.coroutine
    def main():
        pubber()
        forwarder()
        with s.sock.connect('sub', r2) as sub:
            msg = yield sub.recv()
            assert msg == ('topic1', 'asdf [sub.on_recv]')
    s.async.run_sync(main)
    state['send'] = False


def test_push_pull_device():
    r1 = s.sock.route()
    r2 = s.sock.route()
    @s.async.coroutine
    def pusher(x):
        yield s.sock.push(r1, 'job{}'.format(x))
    @s.async.coroutine
    def main():
        pusher(1)
        pusher(2)
        with s.sock.connect('pull', r2) as pull:
            responses = set()
            for _ in range(2):
                msg = yield pull.recv()
                responses.add(msg)
        assert responses == {'job1', 'job2'}
    s.proc.new(s.sock.device, 'streamer', r1, r2)
    s.async.run_sync(main)


def test_sub_sync():
    route = s.sock.route()
    def fn():
        assert s.sock.sub_sync(route) == ('', 'asdf')
    @s.async.coroutine
    def main():
        with s.sock.bind('pub', route) as sock:
            for _ in range(100):
                yield s.async.sleep(.001)
                yield sock.send('asdf')
    proc = s.proc.new(fn)
    s.async.run_sync(main)
    proc.join()
    assert proc.exitcode == 0, proc.exitcode


def test_sub_sync_subscriptions():
    route = s.sock.route()
    def fn():
        data = set()
        for _ in range(10):
            data.add(s.sock.sub_sync(route))
        assert data == {('a', 'asdf1'), ('b', 'asdf2')}
        data = set()
        for _ in range(10):
            data.add(s.sock.sub_sync(route, subscriptions=['b']))
        assert data == {('b', 'asdf2')}
    @s.async.coroutine
    def main():
        with s.sock.bind('pub', route) as sock:
            yield s.async.sleep(.1)
            for _ in range(1000):
                yield sock.send('asdf2', topic='b')
                yield sock.send('asdf1', topic='a')
    proc = s.proc.new(fn)
    s.async.run_sync(main)
    proc.join()
    assert proc.exitcode == 0


def test_push_sync():
    route = s.sock.route()
    s.proc.new(s.sock.push_sync, route, 'asdf')
    @s.async.coroutine
    def main():
        with s.sock.bind('pull', route) as sock:
            msg = yield sock.recv()
        assert msg == 'asdf'
    s.async.run_sync(main)


def test_pull_sync():
    route = s.sock.route()
    def fn():
        assert s.sock.pull_sync(route) == 'asdf'
    @s.async.coroutine
    def main():
        with s.sock.bind('push', route) as sock:
            yield sock.send('asdf')
    proc = s.proc.new(fn)
    s.async.run_sync(main)
    proc.join()
    assert proc.exitcode == 0, proc.exitcode


def test_push_timeout():
    @s.async.coroutine
    def main():
        with s.sock.bind('push', s.sock.route()) as sock:
            yield sock.send('', timeout=.001)
    with pytest.raises(s.sock.Timeout):
        s.async.run_sync(main)


def test_pull_timeout():
    @s.async.coroutine
    def main():
        with s.sock.bind('pull', s.sock.route()) as sock:
            yield sock.send('', timeout=.001)
    with pytest.raises(s.sock.Timeout):
        s.async.run_sync(main)


def test_pull_sync_timeout():
    with pytest.raises(s.sock.Timeout):
        s.sock.pull_sync(s.sock.route(), timeout=.001)


def test_sub_sync_timeout():
    with pytest.raises(s.sock.Timeout):
        s.sock.sub_sync(s.sock.route(), timeout=.001)
