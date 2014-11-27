from __future__ import absolute_import, print_function
import contextlib
import tornado.web
import tornado.ioloop
import s
import requests
import time
import six


def _new_handler_method(fn):
    assert getattr(fn, '_is_coroutine', False), '{} should be a s.async.coroutine'.format(s.func.name(fn))
    @s.async.coroutine(trace=False)
    def method(self, **arguments):
        request = _request_to_dict(self.request, arguments)
        response = yield fn(request)
        _mutate_handler(response, self)
    return method


def _verbs_to_handler(**verbs):
    class Handler(tornado.web.RequestHandler):
        for verb, fn in verbs.items():
            locals()[verb.lower()] = _new_handler_method(fn)
        del verb, fn
    return Handler


def _mutate_handler(response, handler):
    handler.write(response.get('body', 'ok'))
    handler.set_status(response.get('code', 200))
    for header, value in response.get('headers', {}).items():
        handler.set_header(header, value)


def _query_parse(query):
    parsed = six.moves.urllib.parse.parse_qs(query, True)
    return {k: v if len(v) > 1 else v.pop()
            for k, v in parsed.items()}


def _request_to_dict(obj, arguments):
    return {'verb': obj.method.lower(),
            'uri': obj.uri,
            'path': obj.path,
            'query': _query_parse(obj.query),
            'headers': dict(obj.headers),
            'body': obj.body,
            'arguments': arguments}


def _parse_path(path):
    return '/'.join(['(?P<{}>.*)'.format(x[1:])
                     if x.startswith(':')
                     else x
                     for x in path.split('/')])


def server(routes, debug=False):
    routes = [(_parse_path(path), _verbs_to_handler(**verbs))
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
        except requests.exceptions.ConnectionError:
            time.sleep(1e-6)
    try:
        yield url
    except:
        raise
    finally:
        proc.terminate()
