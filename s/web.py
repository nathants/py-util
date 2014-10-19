from __future__ import absolute_import, print_function
import contextlib
import tornado.web
import tornado.ioloop
import s
import requests
import time


def new_handler_method(fn):
    def method(self, *captures):
        request = request_to_dict(self.request, captures)
        response = fn(request)
        modify_handler(response, self)
    return method


def verbs_to_handler(**verbs):
    class Handler(tornado.web.RequestHandler):
        for verb, fn in verbs.items():
            locals()[verb.lower()] = new_handler_method(fn)
        del verb, fn
    return Handler


def modify_handler(response, handler):
    handler.write(response.get('body', 'ok'))
    handler.set_status(response.get('code', 200))
    for header, value in response.get('headers', {'ring-ish-server': 'yes'}).items():
        handler.set_header(header, value)


def request_to_dict(obj, captures):
    return {'verb': obj.method.lower(),
            'uri': obj.uri,
            'path': obj.path,
            'query': obj.query,
            'headers': dict(obj.headers),
            'body': obj.body,
            'arguments': obj.arguments,
            'captures': captures}


def server(routes, debug=False):
    routes = [(path, verbs_to_handler(**verbs))
              for path, verbs in routes]
    return tornado.web.Application(routes, debug=debug)


@contextlib.contextmanager
def test(app):
    port = s.net.free_port()
    url = 'http://localhost:{}/'.format(port)
    def run():
        app.listen(port)
        tornado.ioloop.IOLoop.current().start()
    proc = s.proc.new(run)
    while True:
        try:
            str(requests.get(url)) # wait for http requests to succeed
            break
        except:
            time.sleep(1e-6)
    try:
        yield url
    except:
        raise
    finally:
        proc.terminate()
