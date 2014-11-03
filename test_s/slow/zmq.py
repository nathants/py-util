from __future__ import print_function, absolute_import
import s
import time
import uuid
import s.zmq
import stopit


_kw = {'timeout': 1000}


def test_push_pull_tcp():
    with stopit.SignalTimeout(seconds=1):
        port = str(s.net.free_port())
        def fn():
            with s.zmq.socket('PUSH bind tcp://*:{port}' + port, **_kw) as push:
                push.send_string('asdf')
        s.thread.new(fn)
        with s.zmq.socket('PULL connect tcp://localhost:' + port, **_kw) as pull:
            assert pull.recv_string() == 'asdf'


def test_push_pull_reverse_connect_bind_order():
    with stopit.SignalTimeout(seconds=1):
        name = str(uuid.uuid4())
        def fn():
            with s.zmq.socket('PUSH connect ipc:///tmp/' + name, **_kw) as push:
                push.send_string('asdf')
        s.thread.new(fn)
        with s.zmq.socket('PULL bind ipc:///tmp/' + name, **_kw) as pull:
            assert pull.recv_string() == 'asdf'


def test_push_pull():
    with stopit.SignalTimeout(seconds=1):
        name = str(uuid.uuid4())
        def fn():
            with s.zmq.socket('PUSH bind ipc:///tmp/' + name, **_kw) as push:
                push.send_string('asdf')
        s.thread.new(fn)
        with s.zmq.socket('PULL connect ipc:///tmp/' + name, **_kw) as pull:
            assert pull.recv_string() == 'asdf'


def test_req_rep():
    with stopit.SignalTimeout(seconds=1):
        name = str(uuid.uuid4())
        def fn():
            with s.zmq.socket('REP bind ipc:///tmp/' + name, **_kw) as rep:
                msg = rep.recv_string()
                rep.send_string('thanks for: ' + msg)
        s.thread.new(fn)
        with s.zmq.socket('REQ connect ipc:///tmp/' + name, **_kw) as req:
            req.send_string('asdf')
            assert 'thanks for: asdf' == req.recv_string()


def test_pub_sub():
    name = str(uuid.uuid4())
    send = True
    def fn():
        with s.zmq.socket('PUB bind ipc:///tmp/' + name, **_kw) as pub:
            while send:
                pub.send_multipart_string(['topic1', 'asdf'])
                time.sleep(.001)
    s.thread.new(fn)
    with s.zmq.socket('SUB connect ipc:///tmp/' + name, **_kw) as sub:
        assert sub.recv_multipart_string() == ['topic1', 'asdf']
        send = False


def test_pub_sub_subscriptions():
    name = str(uuid.uuid4())
    send = True
    def fn():
        with s.zmq.socket('PUB bind ipc:///tmp/' + name, **_kw) as pub:
            while send:
                pub.send_multipart_string(['topic1', 'asdf'])
                pub.send_multipart_string(['topic2', '123'])
                time.sleep(.001)
    s.thread.new(fn)
    with s.zmq.socket('SUB connect ipc:///tmp/' + name, subscriptions=['topic1'], **_kw) as sub:
        assert sub.recv_multipart_string() == ['topic1', 'asdf']
        assert sub.recv_multipart_string() == ['topic1', 'asdf']
        send = False


def test_req_rep_device():
    req_name = str(uuid.uuid4())
    rep_name = str(uuid.uuid4())
    def rep(x):
        with s.zmq.socket('REP connect ipc:///tmp/' + rep_name, **_kw) as rep:
            msg = rep.recv_string()
            rep.send_string('thanks for: {msg}, from rep{x}'.format(**locals()))
    s.thread.new(rep, 1)
    s.thread.new(rep, 2)
    s.thread.new(s.zmq.device, 'QUEUE ipc:///tmp/{req_name} ipc:///tmp/{rep_name}'.format(**locals()))
    with s.zmq.socket('REQ connect ipc:///tmp/' + req_name, **_kw) as req:
        responses = set()
        for _ in range(2):
            req.send_string('asdf')
            responses.add(req.recv_string())
        assert responses == {'thanks for: asdf, from rep1',
                             'thanks for: asdf, from rep2'}


def test_req_rep_device_middleware():
    req_name = str(uuid.uuid4())
    rep_name = str(uuid.uuid4())
    def rep():
        with s.zmq.socket('REP connect ipc:///tmp/' + rep_name, **_kw) as rep:
            msg = rep.recv_string()
            rep.send_string('thanks for: ' + msg)
    def queue():
        with s.zmq.socket('ROUTER bind ipc:///tmp/' + req_name, stream=True) as router:
            with s.zmq.socket('DEALER bind ipc:///tmp/' + rep_name, stream=True) as dealer:
                @router.on_recv
                def router_on_recv(msg):
                    msg[-1] = msg[-1] + b' [router.on_recv]'
                    dealer.send_multipart(msg)
                @dealer.on_recv
                def dealer_on_recv(msg):
                    msg[-1] = msg[-1] + b' [dealer.on_recv]'
                    router.send_multipart(msg)
                s.zmq.ioloop().start()
    s.thread.new(rep)
    s.thread.new(queue)
    with s.zmq.socket('REQ connect ipc:///tmp/' + req_name, **_kw) as req:
        req.send_string('asdf')
        assert req.recv_string() == 'thanks for: asdf [router.on_recv] [dealer.on_recv]'


def test_pub_sub_device():
    pass


def test_pub_sub_device_middleware():
    pass


def test_push_pull_device():
    pass


def test_push_pull_device_middleware():
    pass
