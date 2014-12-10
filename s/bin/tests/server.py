import tornado.web
import tornado.websocket
import s


_conns = []
_port = 8888
_state = {}


def start():
    class Handler(tornado.websocket.WebSocketHandler):
        def check_origin(self, origin):
            return True
        def open(self):
            _conns.append(self)
            send()
        def on_close(self):
            with s.exceptions.ignore():
                _conns.remove(self)
    assert s.net.port_free(_port), 'something already running on port: {}'.format(_port)
    tornado.web.Application([(r'/ws', Handler)]).listen(_port)


def send(test_datas=None):
    if test_datas:
        _state['last'] = test_datas
    test_datas = _state.get('last') or []
    if any(y['result'] for x in test_datas for y in x):
        message = 'red'
    else:
        message = 'green'
    for c in _conns:
        c.write_message(message)
