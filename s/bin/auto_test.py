from __future__ import absolute_import, print_function
import blessed
import tornado.websocket
import tornado.ioloop
import tornado.web
import s
import argh


_conns = []
_port = 8888


def _server():
    class Handler(tornado.websocket.WebSocketHandler):
        def check_origin(self, origin):
            return True
        def open(self):
            _conns.append(self)
        def on_close(self):
            with s.exceptions.ignore():
                _conns.remove(self)
    tornado.web.Application([(r'/ws', Handler)]).listen(_port)
    tornado.ioloop.IOLoop.instance().start()


def _view(test_data):
    failures = [x['result'] for x in test_data if x['result']]
    color = s.colors.red if failures else s.colors.green
    name = test_data[0]['path'].split(':')[0]
    val = color(name)
    for failure in failures:
        val += '\n' + failure
    return val


@s.fn.badfunc
def _write_to_conns(test_datas):
    message = 'green'
    if any(y['result'] for x in test_datas for y in x):
        message = 'red'
    for c in _conns:
        c.write_message(message)


def _print(terminal, text):
    print(terminal.clear)
    print(terminal.move(0, 0))
    print(text)
    print(terminal.move(0, 0)) # hide_cursor broken in multi-term in emacs


def _app(terminal):
    last = None
    for test_datas in s.test.run_tests_auto():
        _write_to_conns(test_datas)
        text = '\n'.join(map(_view, test_datas))
        if text != last:
            last = text
        _print(terminal, text)


def _main():
    s.log.setup()
    assert s.net.port_free(_port), 'something already running on port: {}'.format(_port)
    s.thread.new(_server)
    terminal = blessed.Terminal()
    with terminal.fullscreen():
        with terminal.hidden_cursor():
            _app(terminal)


def main():
    argh.dispatch_command(_main)
