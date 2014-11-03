from __future__ import print_function, absolute_import
import s
import time
import uuid
import s.zmq


_kw = {'timeout': 1000}


def test_push_pull_tcp():
    route = 'tcp://localhost:{}'.format(s.net.free_port())

    # when we push a message on tcp
    def pusher():
        with s.zmq.socket('PUSH', 'bind', route.replace('localhost', '*'), **_kw) as push:
            push.send_string('asdf')
    s.thread.new(pusher)

    # then we should pull that same message
    with s.zmq.socket('PULL', 'connect', route, **_kw) as pull:
        assert pull.recv_string() == 'asdf'


def test_push_pull_reverse_connect_bind_order():
    route = 'ipc:///tmp/{}'.format(uuid.uuid4())

    # when we push a message on a connect socket
    def pusher():
        with s.zmq.socket('PUSH', 'connect', route, **_kw) as push:
            push.send_string('asdf')
    s.thread.new(pusher)

    # then we should pull that same message on a bind socket
    with s.zmq.socket('PULL', 'bind', route, **_kw) as pull:
        assert pull.recv_string() == 'asdf'


def test_push_pull():
    route = 'ipc:///tmp/{}'.format(uuid.uuid4())

    # when we push a message on a bind socket
    def pusher():
        with s.zmq.socket('PUSH', 'bind', route, **_kw) as push:
            push.send_string('asdf')
    s.thread.new(pusher)

    # then we should pull that same message on a connect socket
    with s.zmq.socket('PULL', 'connect', route, **_kw) as pull:
        assert pull.recv_string() == 'asdf'


def test_req_rep():
    route = 'ipc:///tmp/{}'.format(uuid.uuid4())

    # when we have a replier
    def replier():
        with s.zmq.socket('REP', 'bind', route, **_kw) as rep:
            msg = rep.recv_string()
            rep.send_string('thanks for: ' + msg)
    s.thread.new(replier)

    # then we should see it reply to a request
    with s.zmq.socket('REQ', 'connect', route, **_kw) as req:
        req.send_string('asdf')
        assert 'thanks for: asdf' == req.recv_string()


def test_pub_sub():
    route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    state = {'send': True}

    # when we publish messages
    def pubber():
        with s.zmq.socket('PUB', 'bind', route, **_kw) as pub:
            while state['send']:
                pub.send_multipart_string(['topic1', 'asdf'])
                time.sleep(.001)
    s.thread.new(pubber)

    # then we should be able to subscribe to those messages
    with s.zmq.socket('SUB', 'connect', route, **_kw) as sub:
        assert sub.recv_multipart_string() == ['topic1', 'asdf']
        state['send'] = False


def test_pub_sub_subscriptions():
    route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    state = {'send': True}

    # when we publish messages on multiple topics
    def pubber():
        with s.zmq.socket('PUB', 'bind', route, **_kw) as pub:
            while state['send']:
                pub.send_multipart_string(['topic1', 'asdf'])
                pub.send_multipart_string(['topic2', '123'])
                time.sleep(.001)
    s.thread.new(pubber)

    # then we should be able to subscribe to specific topics
    with s.zmq.socket('SUB', 'connect', route, subscriptions=['topic1'], **_kw) as sub:
        assert sub.recv_multipart_string() == ['topic1', 'asdf']
        assert sub.recv_multipart_string() == ['topic1', 'asdf']
        state['send'] = False


def test_req_rep_device():
    req_route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    rep_route = 'ipc:///tmp/{}'.format(uuid.uuid4())

    # when we have multiple repliers connected to a device
    def replier(x):
        with s.zmq.socket('REP', 'connect', rep_route, **_kw) as rep:
            msg = rep.recv_string()
            rep.send_string('thanks for: {msg}, from rep{x}'.format(**locals()))
    s.thread.new(replier, 1)
    s.thread.new(replier, 2)
    s.thread.new(s.zmq.device, 'QUEUE', req_route, rep_route, **_kw)

    # then we should see our requests to that device fair queued among them
    with s.zmq.socket('REQ', 'connect', req_route, **_kw) as req:
        responses = set()
        for _ in range(2):
            req.send_string('asdf')
            responses.add(req.recv_string())
        assert responses == {'thanks for: asdf, from rep1',
                             'thanks for: asdf, from rep2'}


def test_req_rep_device_middleware():
    req_route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    rep_route = 'ipc:///tmp/{}'.format(uuid.uuid4())

    # when we have a replier connected to a device with middleware
    def replier():
        with s.zmq.socket('REP', 'connect', rep_route, **_kw) as rep:
            msg = rep.recv_string()
            rep.send_string('thanks for: ' + msg)
    def queue():
        with s.zmq.socket('ROUTER', 'bind', req_route, async=True, **_kw) as router:
            with s.zmq.socket('DEALER', 'bind', rep_route, async=True, **_kw) as dealer:
                @router.on_recv
                def router_on_recv(msg):
                    msg[-1] = msg[-1] + b' [router.on_recv]'
                    dealer.send_multipart(msg)
                @dealer.on_recv
                def dealer_on_recv(msg):
                    msg[-1] = msg[-1] + b' [dealer.on_recv]'
                    router.send_multipart(msg)
                s.zmq.ioloop().start()
    s.thread.new(replier)
    s.thread.new(queue)

    # then we should see our requests to that device affected by that middleware
    with s.zmq.socket('REQ', 'connect', req_route, **_kw) as req:
        req.send_string('asdf')
        assert req.recv_string() == 'thanks for: asdf [router.on_recv] [dealer.on_recv]'
        s.zmq.ioloop().stop()


def test_pub_sub_device():
    sub_route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    pub_route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    state = {'send': True}

    # when we have multiple publishers connected to a device
    def pubber(x):
        with s.zmq.socket('PUB', 'connect', sub_route, **_kw) as pub:
            while state['send']:
                pub.send_multipart_string(['topic{}'.format(x), 'asdf'])
                time.sleep(.01)
    s.thread.new(pubber, 1)
    s.thread.new(pubber, 2)
    s.thread.new(s.zmq.device, 'FORWARDER', sub_route, pub_route, **_kw)

    # then we should see all of their messages when we subscribe to that device
    with s.zmq.socket('SUB', 'connect', pub_route, **_kw) as sub:
        responses = {tuple(sub.recv_multipart_string()) for _ in range(100)}
        assert responses == {('topic1', 'asdf'),
                             ('topic2', 'asdf')}
        state['send'] = False


def test_pub_sub_device_middleware():
    sub_route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    pub_route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    state = {'send': True}

    # when we have a publisher connected to a device with middleware
    def pubber():
        with s.zmq.socket('PUB', 'connect', sub_route, **_kw) as pub:
            while state['send']:
                pub.send_multipart_string(['topic1', 'asdf'])
                time.sleep(.01)
    def forwarder():
        with s.zmq.socket('SUB', 'bind', sub_route, async=True, **_kw) as sub:
            with s.zmq.socket('PUB', 'bind', pub_route, async=True, **_kw) as pub:
                @sub.on_recv
                def sub_on_recv(msg):
                    msg[-1] = msg[-1] + b' [sub.on_recv]'
                    pub.send_multipart(msg)
                s.zmq.ioloop().start()
    s.thread.new(pubber)
    s.thread.new(forwarder)

    # then we should see the messages effected by that middleware
    with s.zmq.socket('SUB', 'connect', pub_route, **_kw) as sub:
        assert sub.recv_multipart_string() == ['topic1', 'asdf [sub.on_recv]']
        state['send'] = False
        s.zmq.ioloop().stop()


def test_push_pull_device():
    pull_route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    push_route = 'ipc:///tmp/{}'.format(uuid.uuid4())

    # when we have multiple pushers connected to a device
    def pusher(x):
        with s.zmq.socket('PUSH', 'connect', pull_route, **_kw) as push:
            push.send_string('job{}'.format(x))
    s.thread.new(pusher, 1)
    s.thread.new(pusher, 2)
    s.thread.new(s.zmq.device, 'STREAMER', pull_route, push_route, **_kw)

    # then we should see receive all of their messages when we pull on that device
    with s.zmq.socket('PULL', 'connect', push_route, **_kw) as pull:
        responses = {pull.recv_string() for _ in range(2)}
        assert responses == {'job1', 'job2'}


def test_push_pull_device_middleware():
    pull_route = 'ipc:///tmp/{}'.format(uuid.uuid4())
    push_route = 'ipc:///tmp/{}'.format(uuid.uuid4())

    # when we have a pusher connected to a device with middleware
    def pusher():
        with s.zmq.socket('PUSH', 'connect', pull_route, **_kw) as push:
            push.send_string('job1')
    def streamer():
        with s.zmq.socket('PULL', 'bind', pull_route, async=True, **_kw) as pull:
            with s.zmq.socket('PUSH', 'bind', push_route, async=True, **_kw) as push:
                @pull.on_recv
                def pull_on_recv(msg):
                    push.send(msg[0] + b' [pull.on_recv]')
                s.zmq.ioloop().start()
    s.thread.new(pusher)
    s.thread.new(streamer)

    # then we should see the message effected by that middleware
    with s.zmq.socket('PULL', 'connect', push_route, **_kw) as pull:
        assert pull.recv_string() == 'job1 [pull.on_recv]'
        s.zmq.ioloop().stop()
