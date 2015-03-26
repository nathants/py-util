from __future__ import absolute_import, print_function
import logging
import s.thread
import mock
import functools
import traceback
import json
import types
import contextlib
import datetime
import tornado.web
import tornado.httputil
import tornado.httpclient
import s.func
import s.async
import s.proc
import s.data
import s.exceptions
import s.log
import s.schema
import s.net
import s.hacks
import requests
import time
import six


class schemas:
    json = (':or',) + s.data.json_types

    request = {'verb': str,
               'url': str,
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
    name = s.func.name(fn)
    @tornado.gen.coroutine
    def method(self, **args):
        request = _request_to_dict(self.request, args)
        try:
            response = yield fn(request)
        except:
            logging.exception('uncaught exception in: %s', name)
            response = {'code': 500}
        _set_handler_response(response, self)
    method.fn = fn
    return method


@s.schema.check(_kwargs={str: types.FunctionType}, _return=type)
def _verbs_to_handler(**verbs):
    class Handler(tornado.web.RequestHandler):
        for verb, fn in verbs.items():
            locals()[verb.lower()] = _new_handler_method(fn)
        del verb, fn
    return Handler


@s.schema.check(schemas.response, tornado.web.RequestHandler)
def _set_handler_response(response, handler):
    body = response.get('body', '')
    body = body if isinstance(body, s.data.string_types + (bytes,)) else json.dumps(body)
    handler.write(body)
    handler.set_status(response.get('code', 200), response.get('reason', ''))
    for header, value in response.get('headers', {}).items():
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
            'url': obj.uri,
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


# TODO this schema is particularly verbose...
@contextlib.contextmanager
# @s.schema.check((':or', lambda x: callable(x), tornado.web.Application), poll=(':or', bool, str), before_start=lambda x: callable(x), _freeze=False)
def test(app, poll='/', context=lambda: mock.patch.object(mock, '_fake_', create=True), use_thread=False):
    port = s.net.free_port()
    url = 'http://0.0.0.0:{}'.format(port)
    def run():
        with context():
            if isinstance(app, tornado.web.Application):
                app.listen(port)
            else:
                app().listen(port)
            if not use_thread:
                tornado.ioloop.IOLoop.current().start()
    proc = (s.thread.new if use_thread else s.proc.new)(run)
    if poll:
        wait_for_http(url + poll)
    try:
        yield url
    except:
        raise
    finally:
        if not use_thread:
            proc.terminate()


with s.exceptions.ignore(ImportError):
    tornado.httpclient.AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")


class Blowup(Exception):
    def __init__(self, message, code, reason, body):
        super().__init__(message)
        self.code = code
        self.reason = reason
        self.body = _try_decode(body)

    def __str__(self):
        return '{}, code={}, reason="{}"\n{}'.format(self.args[0] if self.args else '', self.code, self.reason, self.body)


# TODO this should probably be an argument to something
faux_app = None


@tornado.gen.coroutine
@s.schema.check(str, str, timeout=(':or', int, float), blowup=bool, body=schemas.json, query=dict, _kwargs=dict, _return=schemas.response)
def _fetch(verb, url, **kw):
    fetcher = _faux_fetch if faux_app else _real_fetch
    raise tornado.gen.Return((yield fetcher(verb, url, **kw)))


def _parse_body(body):
    body = _try_decode(body or b'')
    with s.exceptions.ignore(ValueError, TypeError):
        body = json.loads(body)
    return body


@tornado.gen.coroutine
def _real_fetch(verb, url, **kw):
    url, timeout, blowup, kw = _process_kwargs(url, kw)
    request = tornado.httpclient.HTTPRequest(url, method=verb, **kw)
    future = tornado.concurrent.Future()
    response = tornado.httpclient.AsyncHTTPClient().fetch(request, callback=lambda x: future.set_result(x))
    if timeout:
        tornado.ioloop.IOLoop.current().add_timeout(
            datetime.timedelta(seconds=timeout),
            lambda: not future.done() and future.set_exception(Timeout())
        )
    response = yield future
    if blowup and response.code != 200:
        raise Blowup('{verb} {url} did not return 200, returned {code}'.format(code=response.code, **locals()),
                     response.code,
                     response.reason,
                     response.body)
    raise tornado.gen.Return({'code': response.code,
                              'reason': response.reason,
                              'headers': {k.lower(): v for k, v in response.headers.items()},
                              'body': _parse_body(response.body or b'')})


@tornado.gen.coroutine
def _faux_fetch(verb, url, **kw):
    assert isinstance(faux_app, tornado.web.Application)
    query = kw.get('query', {})
    url, _, blowup, kw = _process_kwargs(url, kw)
    dispatcher = tornado.web._RequestDispatcher(faux_app, None)
    dispatcher.set_request(tornado.httputil.HTTPServerRequest(method=verb, uri=url, **kw))
    args = dispatcher.path_kwargs
    try:
        handler = getattr(dispatcher.handler_class, verb.lower()).fn
    except AttributeError:
        raise Exception('no route matched: {verb} {url}'.format(**locals()))
    request = {'verb': verb,
               'url': url,
               'path': '/' + url.split('://')[-1].split('/', 1)[-2],
               'query': query,
               'body': _parse_body(kw.get('body', b'')),
               'headers': kw.get('headers', {}),
               'args': {k: _try_decode(v) for k, v in args.items()}}
    response = (yield handler(request))
    if blowup and response.get('code', 200) != 200:
        raise Blowup('{verb} {url} did not return 200, returned {code}'.format(code=response['code'], **locals()),
                     response['code'],
                     response.get('reason', ''),
                     response.get('body', ''))
    raise tornado.gen.Return(response)


def _process_kwargs(url, kw):
    timeout = kw.pop('timeout', 10)
    if 'body' in kw and not isinstance(kw['body'], s.data.string_types + (bytes,)):
        kw['body'] = json.dumps(kw['body'])
    blowup = kw.pop('blowup', False)
    if 'query' in kw:
        assert '?' not in url, 'you cannot user keyword arg query and have ? already in the url: {url}'.format(**locals())
        url += '?' + '&'.join('{}={}'.format(k, tornado.escape.url_escape(v if isinstance(v, s.data.string_types) else json.dumps(v)))
                              for k, v in kw.pop('query').items())
    return url, timeout, blowup, kw


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


@s.func.optionally_parameterized_decorator
def validate(*args, **kwargs):
    def decorator(decoratee):
        name = s.func.name(decoratee)
        request_schema = s.schema._get_schemas(decoratee, args, kwargs)['arg'][0]
        decoratee = s.schema.check(*args, **kwargs)(decoratee)
        @functools.wraps(decoratee)
        @tornado.gen.coroutine
        def decorated(request):
            try:
                s.schema._validate(request_schema, request)
            except s.schema.Error:
                raise tornado.gen.Return({'code': 403, 'reason': 'your request is not valid', 'body': traceback.format_exc() + '\nvalidation failed for: {}'.format(name)})
            else:
                raise tornado.gen.Return((yield decoratee(request)))
        return decorated
    return decorator
