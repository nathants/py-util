from __future__ import absolute_import, print_function
import contextlib
import datetime
import tornado.web
import tornado.httputil
import tornado.ioloop
import tornado.httpclient
import s
import requests
import time
import six


class schemas:
    request = {'verb': str,
               'uri': str,
               'path': str,
               'query': {str: (':or', str, [str])},
               'body': str,
               'headers': {str: str},
               'arguments': {str: str}}

    response = {'code': int,
                'reason': str,
                'headers': {str: str},
                'body': str}


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


@s.schema.check(tornado.httputil.HTTPServerRequest, {str: str}, returns=schemas.request)
def _request_to_dict(obj, arguments):
    return {'verb': obj.method.lower(),
            'uri': obj.uri,
            'path': obj.path,
            'query': _query_parse(obj.query),
            'body': obj.body.decode('utf-8'),
            'headers': dict(obj.headers),
            'arguments': arguments}


def _parse_path(path):
    return '/'.join(['(?P<{}>.*)'.format(x[1:])
                     if x.startswith(':')
                     else x
                     for x in path.split('/')])


def app(routes, debug=False):
    routes = [(_parse_path(path), _verbs_to_handler(**verbs))
              for path, verbs in routes]
    return tornado.web.Application(routes, debug=debug)


@contextlib.contextmanager
def test(app, poll=True):
    port = s.net.free_port()
    url = 'http://localhost:{}/'.format(port)
    def run():
        app.listen(port)
        tornado.ioloop.IOLoop.current().start()
    proc = s.proc.new(run)
    if poll:
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


with s.exceptions.ignore(ImportError):
    tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")


@s.schema.check(str, str, returns=schemas.response, timeout=float, kwargs=dict)
@s.async.coroutine(freeze=False)
def _fetch(method, url, **kw):
    timeout = kw.pop('timeout', None)
    request = tornado.httpclient.HTTPRequest(url, method=method, **kw)
    future = s.async.Future()
    response = tornado.httpclient.AsyncHTTPClient().fetch(request)
    s.async.chain(response, future)
    if timeout:
        s.async.ioloop().add_timeout(
            datetime.timedelta(seconds=timeout),
            lambda: not future.done() and future.set_exception(Timeout)
        )
    response = yield future
    raise s.async.Return({'code': response.code,
                          'reason': response.reason,
                          'headers': {k.lower(): v for k, v in response.headers.items()},
                          'body': response.body.decode('utf-8')})


def get(url, **kw):
    return _fetch('GET', url, **kw)


def post(url, body, **kw):
    return _fetch('POST', url, body=body, **kw)


get_sync = s.async.make_sync(get)
post_sync = s.async.make_sync(post)


class Timeout(Exception):
    pass
