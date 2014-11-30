from __future__ import print_function, absolute_import
import pytest
import s
import time
import s.sock


kw = {'timeout': 1000}


def test_cannot_use_none_as_message():
    @s.async.coroutine
    def main():
        yield s.sock.push(s.sock.new_ipc_route(), None)
    with pytest.raises(AssertionError):
        s.async.run_sync(main)


def test_pub_sub():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pubber():
        with s.sock.bind('pub', route, **kw) as pub:
            while True:
                yield pub.send('asdf')
                yield s.async.sleep(.001)
    @s.async.coroutine
    def subber():
        pubber()
        with s.sock.connect('sub', route, **kw) as sock:
            topic, msg = yield sock.recv()
        assert msg == 'asdf'
    s.async.run_sync(subber)


def test_push_pull_reversed_connect_bind():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        with s.sock.bind('push', route, **kw) as sock:
            yield sock.send('asdf')
    @s.async.coroutine
    def puller():
        pusher()
        msg = yield s.sock.pull(route, **kw)
        assert msg == 'asdf'
    s.async.run_sync(puller)


def test_push_pull_tcp():
    route = 'tcp://0.0.0.0:{}'.format(s.net.free_port())
    @s.async.coroutine
    def pusher():
        yield s.sock.push(route, 'asdf', **kw)
    @s.async.coroutine
    def puller():
        pusher()
        with s.sock.bind('pull', route, **kw) as sock:
            val = yield sock.recv()
            assert val == 'asdf'
    s.async.run_sync(puller)


def test_push_pull():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.push(route, 'asdf', **kw)
    @s.async.coroutine
    def puller():
        pusher()
        with s.sock.bind('pull', route, **kw) as sock:
            val = yield sock.recv()
            assert val == 'asdf'
    s.async.run_sync(puller)


def test_async_methods_error_when_no_ioloop():
    s.async.ioloop().clear()
    with pytest.raises(AssertionError):
        s.sock.bind('pull', s.sock.new_ipc_route(), **kw).recv()
    with pytest.raises(AssertionError):
        s.sock.bind('pull', s.sock.new_ipc_route(), **kw).send('')


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
    r1 = s.sock.new_ipc_route()
    r2 = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher(route, msg, seconds=0):
        yield s.async.sleep(seconds)
        yield s.sock.push(route, msg, **kw)
    @s.async.coroutine
    def main():
        pusher(r1, 'msg1')
        pusher(r2, 'msg2', .1)
        with s.sock.bind('pull', r1, **kw) as p1, s.sock.bind('pull', r2, **kw) as p2, s.sock.timeout(.1) as t:
            sock, msg = yield s.sock.select(p1, p2, t)
            assert msg == 'msg1' and sock == id(p1)
            sock, msg = yield s.sock.select(p1, p2, t)
            assert msg == 'msg2' and sock == id(p2)
            sock, msg = yield s.sock.select(p1, p2, t)
            assert sock == id(t) and msg == ''
    s.async.run_sync(main)


def test_push_pull_device_middleware():
    r1 = s.sock.new_ipc_route()
    r2 = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        yield s.sock.push(r1, 'job1', **kw)
    @s.async.coroutine
    def streamer():
        with s.sock.bind('pull', r1, **kw) as puller, s.sock.bind('push', r2, **kw) as pusher:
            msg = yield puller.recv()
            yield pusher.send(msg + ' [streamer]')
    @s.async.coroutine
    def main():
        pusher()
        streamer()
        msg = yield s.sock.pull(r2, **kw)
        assert msg == 'job1 [streamer]'
    s.async.run_sync(main)


def test_push_pull_data():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pusher():
        with s.sock.bind('push', route, **kw) as sock:
            yield sock.send({'a': '123'})
    @s.async.coroutine
    def puller():
        pusher()
        msg = yield s.sock.pull(route, **kw)
        assert msg == {'a': '123'}
    s.async.run_sync(puller)


def test_req_rep():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def requestor():
        with s.sock.bind('req', route, **kw) as req:
            yield req.send('asdf')
            msg = yield req.recv()
            assert msg == 'asdf!!'
    @s.async.coroutine
    def replier():
        requestor()
        with s.sock.connect('rep', route, **kw) as rep:
            msg = yield rep.recv()
            yield rep.send(msg + '!!')
    s.async.run_sync(replier)


def test_pub_sub_subscriptions():
    route = s.sock.new_ipc_route()
    @s.async.coroutine
    def pubber():
        with s.sock.bind('pub', route, **kw) as pub:
            while True:
                yield pub.send('asdf', topic='a')
                yield pub.send('123', topic='b')
                yield s.async.sleep(.001)
    @s.async.coroutine
    def subber():
        pubber()
        with s.sock.connect('sub', route, **kw) as sock:
            msg = yield sock.recv()
            assert msg == ('a', 'asdf')
            msg = yield sock.recv()
            assert msg == ('b', '123')
        with s.sock.connect('sub', route, subscriptions=['a']) as sock:
            msg = yield sock.recv()
            assert msg == ('a', 'asdf')
            msg = yield sock.recv()
            assert msg == ('a', 'asdf')
    s.async.run_sync(subber)


# def test_req_rep_device():
#     req_route = s.sock.new_ipc_route()
#     rep_route = s.sock.new_ipc_route()
#     def replier(x):
#         rep = s.sock.connect('rep', rep_route, **kw)
#         msg = rep.recv()
#         rep.send('thanks for: {msg}, from rep{x}'.format(**locals()))
#     s.thread.new(replier, 1)
#     s.thread.new(replier, 2)
#     s.thread.new(s.sock.device, 'QUEUE', req_route, rep_route, **kw)
#     req = s.sock.connect('req', req_route, **kw)
#     responses = set()
#     for _ in range(2):
#         req.send('asdf')
#         responses.add(req.recv())
#     assert responses == {'thanks for: asdf, from rep1',
#                          'thanks for: asdf, from rep2'}


# def test_req_rep_device_middleware():
#     req_route = s.sock.new_ipc_route()
#     rep_route = s.sock.new_ipc_route()
#     def replier():
#         rep = s.sock.connect('rep', rep_route, **kw)
#         msg = rep.recv()
#         rep.send('thanks for: ' + msg)
#     def queue():
#         router = s.sock.bind('router', req_route, **kw)
#         dealer = s.sock.bind('dealer', rep_route, **kw)
#         @router.on_recv
#         def router_on_recv(msg):
#             msg[-1] = msg[-1] + b' [router.on_recv]'
#             dealer.send_multipart(msg)
#         @dealer.on_recv
#         def dealer_on_recv(msg):
#             msg[-1] = msg[-1] + b' [dealer.on_recv]'
#             router.send_multipart(msg)
#         s.async.ioloop().start()
#     s.thread.new(replier)
#     s.thread.new(queue)
#     req = s.sock.connect('req', req_route, **kw)
#     req.send('asdf')
#     assert req.recv() == 'thanks for: asdf [router.on_recv] [dealer.on_recv]'
#     s.async.ioloop().stop()


# def test_pub_sub_device():
#     sub_route = s.sock.new_ipc_route()
#     pub_route = s.sock.new_ipc_route()
#     state = {'send': True}
#     def pubber(x):
#         pub = s.sock.connect('pub', sub_route, **kw)
#         while state['send']:
#             pub.send_multipart(['topic{}'.format(x), 'asdf'])
#             time.sleep(.01)
#     s.thread.new(pubber, 1)
#     s.thread.new(pubber, 2)
#     s.thread.new(s.sock.device, 'forwarder', sub_route, pub_route, **kw)
#     sub = s.sock.connect('sub', pub_route, **kw)
#     responses = {tuple(sub.recv_multipart()) for _ in range(100)}
#     assert responses == {('topic1', 'asdf'),
#                          ('topic2', 'asdf')}
#     state['send'] = False


# def test_pub_sub_device_middleware():
#     sub_route = s.sock.new_ipc_route()
#     pub_route = s.sock.new_ipc_route()
#     state = {'send': True}
#     def pubber():
#         pub = s.sock.connect('pub', sub_route, **kw)
#         while state['send']:
#             pub.send_multipart(['topic1', 'asdf'])
#             time.sleep(.01)
#     def forwarder():
#         sub = s.sock.bind('sub', sub_route, **kw)
#         pub = s.sock.bind('pub', pub_route, **kw)
#         @sub.on_recv
#         def sub_on_recv(msg):
#             msg[-1] = msg[-1] + b' [sub.on_recv]'
#             pub.send_multipart(msg)
#         s.async.ioloop().start()
#     s.thread.new(pubber)
#     s.thread.new(forwarder)
#     sub = s.sock.connect('sub', pub_route, **kw)
#     assert sub.recv_multipart() == ['topic1', 'asdf [sub.on_recv]']
#     state['send'] = False
#     s.async.ioloop().stop()


# def test_push_pull_device():
#     pull_route = s.sock.new_ipc_route()
#     push_route = s.sock.new_ipc_route()
#     def pusher(x):
#         s.sock.connect('push', pull_route, **kw).send('job{}'.format(x))
#     s.thread.new(pusher, 1)
#     s.thread.new(pusher, 2)
#     s.thread.new(s.sock.device, 'streamer', pull_route, push_route, **kw)
#     pull = s.sock.connect('pull', push_route, **kw)
#     responses = {pull.recv() for _ in range(2)}
#     assert responses == {'job1', 'job2'}


# def test_push_pull_device_middleware():
#     pull_route = s.sock.new_ipc_route()
#     push_route = s.sock.new_ipc_route()
#     def pusher():
#         s.sock.connect('push', pull_route, **kw).send('job1')
#     def streamer():
#         pull = s.sock.bind('pull', pull_route, **kw)
#         push = s.sock.bind('push', push_route, **kw)
#         @pull.on_recv
#         def pull_on_recv(msg):
#             push.send(msg[0] + b' [pull.on_recv]')
#         s.async.ioloop().start()
#     s.thread.new(pusher)
#     s.thread.new(streamer)
#     assert s.sock.connect('pull', push_route, **kw).recv() == 'job1 [pull.on_recv]'
#     s.async.ioloop().stop()
