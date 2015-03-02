from __future__ import absolute_import, print_function
import json
import types
import contextlib
import datetime
import tornado.web
import tornado.httputil
import tornado.httpclient
import s
import requests
import time
import six


class schemas:
    json = (':or',) + s.data.json_types

    request = {'verb': str,
               'uri': str,
               'path': str,
               'query': {str: (':or', str, [str]) + s.data.json_types},
               'body': json,
               'headers': {str: str},
               'args': {str: str}}

    response = {'code': (':optional', int, 200),
                'reason': (':optional', (':or', str, None), None),
                'headers': (':optional', {str: str}, {}),
                'body': (':optional', (':or', json, str, bytes), '')}


def _try_decode(text):
    try:
        return text.decode('utf-8')
    except:
        return text


def _new_handler_method(fn):
    assert getattr(fn, '_is_coroutine', False), '{} should be a s.async.coroutine'.format(s.func.name(fn))
    @s.async.coroutine(trace=False)
    def method(self, **args):
        request = _request_to_dict(self.request, args)
        response = yield fn(request)
        _mutate_handler(response, self)
    return method


@s.schema.check(_kwargs={str: types.FunctionType}, _return=type)
def _verbs_to_handler(**verbs):
    class Handler(tornado.web.RequestHandler):
        for verb, fn in verbs.items():
            locals()[verb.lower()] = _new_handler_method(fn)
        del verb, fn
    return Handler


@s.schema.check(schemas.response, tornado.web.RequestHandler)
def _mutate_handler(response, handler):
    body = response['body']
    body = body if s.schema.is_valid(str, body) else json.dumps(body)
    handler.write(body)
    handler.set_status(response['code'], response['reason'])
    for header, value in response['headers'].items():
        handler.set_header(header, value)


@s.schema.check(str, _return=schemas.request['query'])
def _query_parse(query):
    parsed = six.moves.urllib.parse.parse_qs(query, True)
    val = {k: v if len(v) > 1 else v.pop()
           for k, v in parsed.items()}
    for k, v in val.items():
        with s.exceptions.ignore(ValueError, TypeError):
            val[k] = json.loads(v)
    return val


@s.schema.check(tornado.httputil.HTTPServerRequest, {str: str}, _return=schemas.request)
def _request_to_dict(obj, args):
    body = _try_decode(obj.body)
    with s.exceptions.ignore(ValueError, TypeError):
        body = json.loads(body)
    return {'verb': obj.method.lower(),
            'uri': obj.uri,
            'path': obj.path,
            'query': _query_parse(obj.query),
            'body': body,
            'headers': dict(obj.headers),
            'args': args}


@s.schema.check(str, _return=str)
def _parse_path(path):
    return '/'.join(['(?P<{}>.*)'.format(x[1:])
                     if x.startswith(':')
                     else x
                     for x in path.split('/')])


@s.schema.check([(str, {str: types.FunctionType})], debug=bool, _return=tornado.web.Application)
def app(routes, debug=False):
    routes = [(_parse_path(path), _verbs_to_handler(**verbs))
              for path, verbs in routes]
    return tornado.web.Application(routes, debug=debug)


def wait_for_http(url):
    while True:
        try:
            with s.log.disable('requests.packages.urllib3.connectionpool'):
                str(requests.get(url)) # wait for http requests to succeed
            break
        except requests.exceptions.ConnectionError:
            time.sleep(1e-6)


@contextlib.contextmanager
@s.schema.check(tornado.web.Application, poll=bool)
def test(app, poll=True):
    port = s.net.free_port()
    url = 'http://localhost:{}/'.format(port)
    def run():
        app.listen(port)
        s.async.ioloop().start()
    proc = s.proc.new(run)
    if poll:
        wait_for_http(url)
    try:
        yield url
    except:
        raise
    finally:
        proc.terminate()


with s.exceptions.ignore(ImportError):
    tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")


@s.async.coroutine(freeze=False)
@s.schema.check(str, str, timeout=(':or', int, float), blowup=bool, body=schemas.json, query=dict, _kwargs=dict, _return=schemas.response)
def _fetch(method, url, **kw):
    timeout = kw.pop('timeout', 10)
    if 'body' in kw and not s.schema.is_valid(str, kw['body']):
        kw['body'] = json.dumps(kw['body'])
    blowup = kw.pop('blowup', False)
    if 'query' in kw:
        assert '?' not in url, 'you cannot user keyword arg query and have ? already in the url: {url}'.format(**locals())
        url += '?' + '&'.join('{}={}'.format(k, tornado.escape.url_escape(v if s.schema.is_valid(str, v) else json.dumps(v)))
                              for k, v in kw.pop('query').items())
    request = tornado.httpclient.HTTPRequest(url, method=method, **kw)
    future = s.async.Future()
    response = tornado.httpclient.AsyncHTTPClient().fetch(request, callback=lambda x: future.set_result(x))
    if timeout:
        s.async.ioloop().add_timeout(
            datetime.timedelta(seconds=timeout),
            lambda: not future.done() and future.set_exception(Timeout())
        )
    response = yield future
    if blowup and response.code != 200:
        raise Blowup('{method} {url} did not return 200, returned {code}'.format(code=response.code, **locals()),
                     response.code,
                     response.reason)
    body = _try_decode(response.body or b'')
    with s.exceptions.ignore(ValueError, TypeError):
        body = json.loads(body)
    raise s.async.Return({'code': response.code,
                          'reason': response.reason,
                          'headers': {k.lower(): v for k, v in response.headers.items()},
                          'body': body})


class Blowup(Exception):
    def __init__(self, message, code, reason):
        super().__init__(message)
        self.code = code
        self.reason = reason


@s.schema.check(str, _kwargs=dict)
def get(url, **kw):
    return _fetch('GET', url, **kw)


# TODO support schema.check for pos/keyword args with default like body
def post(url, body='', **kw):
    return _fetch('POST', url, body=body, **kw)


# TODO make_sync can be a decorator? if not just define these as functions the long way. its better docs.

# get_sync(url, **kw)
get_sync = s.async.make_sync(get)

# post_sync(url, data, **kw)
post_sync = s.async.make_sync(post)


class Timeout(Exception):
    pass
