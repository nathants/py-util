from __future__ import absolute_import, print_function
import blessed
import tornado.websocket
import tornado.ioloop
import threading
import s


conns = []


def server():
    class Handler(tornado.websocket.WebSocketHandler):
        def open(self):
            conns.append(self)
        def on_close(self):
            with s.exceptions.ignore():
                conns.remove(self)
    tornado.web.Application([(r'/ws', Handler)]).listen(8888)
    tornado.ioloop.IOLoop.instance().start()


def view(test_data):
    failures = [x.result for x in test_data if x.result]
    color = s.colors.red if failures else s.colors.green
    name = test_data[0].path.split(':')[0]
    print(color(name))
    for failure in failures:
        print('\n'.join(failure))


def main():
    thread = threading.Thread(target=server)
    thread.daemon = True
    thread.start()

    t = blessed.Terminal()
    with t.fullscreen():
        with t.hidden_cursor():
            for test_datas in s.test.run_tests_auto():
                if conns:
                    message = 'green'
                    if any(y.result for x in test_datas for y in x):
                        message = 'red'
                    for c in conns:
                        c.write_message(message)
                print(t.clear)
                with t.location(0, 0):
                    map(view, test_datas)
