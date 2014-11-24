from __future__ import print_function, absolute_import
import s
import time
import s.sock


_async_kw = {'timeout': 1000}
_sync_kw = s.dicts.merge(_async_kw, {'async': False})


def test_select():
    route1 = s.sock.new_ipc_route()
    route2 = s.sock.new_ipc_route()
    def pusher(route, msg, seconds=0):
        time.sleep(seconds)
        s.sock.bind('push', route, **_sync_kw).send(msg)
    s.thread.new(pusher, route1, 'msg1')
    s.thread.new(pusher, route2, 'msg2', .1)
    @s.async.coroutine
    def main():
        puller1 = s.sock.connect('pull', route1, **_async_kw)
        puller2 = s.sock.connect('pull', route2, **_async_kw)
        timeout = s.sock.timeout(.2)

        [sock, [msg]] = yield s.sock.select(puller1, puller2, timeout)
        assert msg == b'msg1' and sock == id(puller1)

        [sock, [msg]] = yield s.sock.select(puller1, puller2, timeout)
        assert msg == b'msg2' and sock == id(puller2)

        [sock, [msg]] = yield s.sock.select(puller1, puller2, timeout)
        assert sock == id(timeout) and msg == b''

    s.async.run_sync(main)


def test_push_pull_device_middleware_coroutine():
    upstream_route = s.sock.new_ipc_route()
    downstream_route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.connect('push', upstream_route, **_async_kw).send('job1')
    @s.async.coroutine
    def streamer():
        msg = yield s.sock.bind('pull', upstream_route, **_async_kw).recv()
        yield s.sock.bind('push', downstream_route, **_async_kw).send(msg + ' [streamer]')
    @s.async.coroutine
    def main():
        msg = yield s.sock.connect('pull', downstream_route, **_async_kw).recv()
        assert msg == 'job1 [streamer]'
    pusher()
    streamer()
    s.async.run_sync(main)


def test_push_pull_coroutine():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.bind('push', route, **_async_kw).send('asdf')
    @s.async.coroutine
    def puller():
        msg = yield s.sock.connect('pull', route, **_async_kw).recv()
        assert msg == 'asdf'
    pusher()
    s.async.run_sync(puller)


def test_push_pull_coroutine_multipart():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.bind('push', route, **_async_kw).send_multipart(('a', 'b'))
    @s.async.coroutine
    def puller():
        msg = yield s.sock.connect('pull', route, **_async_kw).recv_multipart()
        assert msg == ('a', 'b')
    pusher()
    s.async.run_sync(puller)


def test_push_pull_coroutine_json():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.bind('push', route, **_async_kw).send_json([1, 2])
    @s.async.coroutine
    def puller():
        msg = yield s.sock.connect('pull', route, **_async_kw).recv_json()
        assert msg == (1, 2)
    pusher()
    s.async.run_sync(puller)


def test_req_rep_coroutine():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def requestor():
        req = s.sock.bind('req', route, **_async_kw)
        yield req.send('asdf')
        msg = yield req.recv()
        assert msg == 'asdf!!'
    @s.async.coroutine
    def replier():
        rep = s.sock.connect('rep', route, **_async_kw)
        msg = yield rep.recv()
        yield rep.send(msg + '!!')
    requestor()
    s.async.run_sync(replier)


def test_push_pull_tcp():
    route = 'tcp://localhost:{}'.format(s.net.free_port())
    s.thread.new(lambda: s.sock.bind('push', route.replace('localhost', '*'), **_sync_kw).send('asdf'))
    assert s.sock.connect('pull', route, **_sync_kw).recv() == 'asdf'


def test_push_pull_reverse_connect_bind_order():
    route = s.sock.new_ipc_route()
    s.thread.new(lambda: s.sock.connect('push', route, **_sync_kw).send('asdf'))
    assert s.sock.bind('pull', route, **_sync_kw).recv() == 'asdf'


def test_push_pull():
    route = s.sock.new_ipc_route()
    s.thread.new(lambda: s.sock.bind('push', route, **_sync_kw).send('asdf'))
    assert s.sock.connect('pull', route, **_sync_kw).recv() == 'asdf'


def test_req_rep():
    route = s.sock.new_ipc_route()
    def replier():
        rep = s.sock.bind('rep', route, **_sync_kw)
        msg = rep.recv()
        rep.send('thanks for: ' + msg)
    s.thread.new(replier)
    req = s.sock.connect('req', route, **_sync_kw)
    req.send('asdf')
    assert 'thanks for: asdf' == req.recv()


def test_pub_sub():
    route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.bind('pub', route, **_sync_kw)
        while state['send']:
            pub.send('asdf')
            time.sleep(.001)
    s.thread.new(pubber)
    assert s.sock.connect('sub', route, **_sync_kw).recv() == 'asdf'
    state['send'] = False


def test_pub_sub_multipart():
    route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.bind('pub', route, **_sync_kw)
        while state['send']:
            pub.send_multipart(['', 'asdf'])
            time.sleep(.001)
    s.thread.new(pubber)
    assert s.sock.connect('sub', route, **_sync_kw).recv_multipart() == ['', 'asdf']
    state['send'] = False


def test_pub_sub_subscriptions():
    route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.bind('pub', route, **_sync_kw)
        while state['send']:
            pub.send('topic1 asdf')
            pub.send('topic2 123')
            time.sleep(.001)
    s.thread.new(pubber)
    sub = s.sock.connect('sub', route, subscriptions=['topic1'], **_sync_kw)
    assert sub.recv() == 'topic1 asdf'
    assert sub.recv() == 'topic1 asdf'
    state['send'] = False


def test_pub_sub_subscriptions_multipart():
    route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.bind('pub', route, **_sync_kw)
        while state['send']:
            pub.send_multipart(['topic1', 'asdf'])
            pub.send_multipart(['topic2', '123'])
            time.sleep(.001)
    s.thread.new(pubber)
    sub = s.sock.connect('sub', route, subscriptions=['topic1'], **_sync_kw)
    assert sub.recv_multipart() == ['topic1', 'asdf']
    assert sub.recv_multipart() == ['topic1', 'asdf']
    state['send'] = False


def test_req_rep_device():
    req_route = s.sock.new_ipc_route()
    rep_route = s.sock.new_ipc_route()
    def replier(x):
        rep = s.sock.connect('rep', rep_route, **_sync_kw)
        msg = rep.recv()
        rep.send('thanks for: {msg}, from rep{x}'.format(**locals()))
    s.thread.new(replier, 1)
    s.thread.new(replier, 2)
    s.thread.new(s.sock.device, 'QUEUE', req_route, rep_route, **_sync_kw)
    req = s.sock.connect('req', req_route, **_sync_kw)
    responses = set()
    for _ in range(2):
        req.send('asdf')
        responses.add(req.recv())
    assert responses == {'thanks for: asdf, from rep1',
                         'thanks for: asdf, from rep2'}


def test_req_rep_device_middleware():
    req_route = s.sock.new_ipc_route()
    rep_route = s.sock.new_ipc_route()
    def replier():
        rep = s.sock.connect('rep', rep_route, **_sync_kw)
        msg = rep.recv()
        rep.send('thanks for: ' + msg)
    def queue():
        router = s.sock.bind('router', req_route, **_async_kw)
        dealer = s.sock.bind('dealer', rep_route, **_async_kw)
        @router.on_recv
        def router_on_recv(msg):
            msg[-1] = msg[-1] + b' [router.on_recv]'
            dealer.send_multipart(msg)
        @dealer.on_recv
        def dealer_on_recv(msg):
            msg[-1] = msg[-1] + b' [dealer.on_recv]'
            router.send_multipart(msg)
        s.sock.ioloop().start()
    s.thread.new(replier)
    s.thread.new(queue)
    req = s.sock.connect('req', req_route, **_sync_kw)
    req.send('asdf')
    assert req.recv() == 'thanks for: asdf [router.on_recv] [dealer.on_recv]'
    s.sock.ioloop().stop()


def test_pub_sub_device():
    sub_route = s.sock.new_ipc_route()
    pub_route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber(x):
        pub = s.sock.connect('pub', sub_route, **_sync_kw)
        while state['send']:
            pub.send_multipart(['topic{}'.format(x), 'asdf'])
            time.sleep(.01)
    s.thread.new(pubber, 1)
    s.thread.new(pubber, 2)
    s.thread.new(s.sock.device, 'forwarder', sub_route, pub_route, **_sync_kw)
    sub = s.sock.connect('sub', pub_route, **_sync_kw)
    responses = {tuple(sub.recv_multipart()) for _ in range(100)}
    assert responses == {('topic1', 'asdf'),
                         ('topic2', 'asdf')}
    state['send'] = False


def test_pub_sub_device_middleware():
    sub_route = s.sock.new_ipc_route()
    pub_route = s.sock.new_ipc_route()
    state = {'send': True}
    def pubber():
        pub = s.sock.connect('pub', sub_route, **_sync_kw)
        while state['send']:
            pub.send_multipart(['topic1', 'asdf'])
            time.sleep(.01)
    def forwarder():
        sub = s.sock.bind('sub', sub_route, **_async_kw)
        pub = s.sock.bind('pub', pub_route, **_async_kw)
        @sub.on_recv
        def sub_on_recv(msg):
            msg[-1] = msg[-1] + b' [sub.on_recv]'
            pub.send_multipart(msg)
        s.sock.ioloop().start()
    s.thread.new(pubber)
    s.thread.new(forwarder)
    sub = s.sock.connect('sub', pub_route, **_sync_kw)
    assert sub.recv_multipart() == ['topic1', 'asdf [sub.on_recv]']
    state['send'] = False
    s.sock.ioloop().stop()


def test_push_pull_device():
    pull_route = s.sock.new_ipc_route()
    push_route = s.sock.new_ipc_route()
    def pusher(x):
        s.sock.connect('push', pull_route, **_sync_kw).send('job{}'.format(x))
    s.thread.new(pusher, 1)
    s.thread.new(pusher, 2)
    s.thread.new(s.sock.device, 'streamer', pull_route, push_route, **_sync_kw)
    pull = s.sock.connect('pull', push_route, **_sync_kw)
    responses = {pull.recv() for _ in range(2)}
    assert responses == {'job1', 'job2'}


def test_push_pull_device_middleware():
    pull_route = s.sock.new_ipc_route()
    push_route = s.sock.new_ipc_route()
    def pusher():
        s.sock.connect('push', pull_route, **_sync_kw).send('job1')
    def streamer():
        pull = s.sock.bind('pull', pull_route, **_async_kw)
        push = s.sock.bind('push', push_route, **_async_kw)
        @pull.on_recv
        def pull_on_recv(msg):
            push.send(msg[0] + b' [pull.on_recv]')
        s.sock.ioloop().start()
    s.thread.new(pusher)
    s.thread.new(streamer)
    assert s.sock.connect('pull', push_route, **_sync_kw).recv() == 'job1 [pull.on_recv]'
    s.sock.ioloop().stop()
