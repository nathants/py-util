from __future__ import print_function, absolute_import
import pytest
import s.web
import s.net
import tornado.gen
import tornado.ioloop


def test_non_2XX_codes():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        1 / 0

    app = s.web.app([('/', {'get': handler})])
    with s.web.test(app) as url:
        rep = s.web.get_sync(url)
        assert '1 / 0' not in rep['body']
        assert rep['code'] == 500


def test_normal_app():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        raise tornado.gen.Return({'body': 'asdf'})
    port = s.net.free_port()
    s.web.app([('/', {'get': handler})]).listen(port)
    proc = s.proc.new(tornado.ioloop.IOLoop.current().start)
    url = 'http://0.0.0.0:{port}'.format(**locals())
    assert s.web.get_sync(url)['body'] == 'asdf'
    proc.terminate()


def test_get_timeout():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.sleep(1)
        raise tornado.gen.Return({})

    @tornado.gen.coroutine
    def main(url):
        yield s.web.get(url, timeout=.001)

    app = s.web.app([('/', {'get': handler})])
    with s.web.test(app) as url:
        with pytest.raises(s.web.Timeout):
            s.async.run_sync(lambda: main(url))


def test_get():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        raise tornado.gen.Return({'body': 'ok',
                                  'code': 200,
                                  'headers': {'foo': 'bar'}})

    @tornado.gen.coroutine
    def main(url):
        resp = yield s.web.get(url)
        assert resp['body'] == 'ok'
        assert resp['code'] == 200
        assert resp['headers']['foo'] == 'bar'

    app = s.web.app([('/', {'get': handler})])
    with s.web.test(app) as url:
        s.async.run_sync(lambda: main(url))


def test_get_params_json():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        raise tornado.gen.Return({'body': request['query']})

    @tornado.gen.coroutine
    def main(url):
        resp = yield s.web.get(url, query={'data': [1, 2, 3]})
        assert resp['body'] == {'data': [1, 2, 3]}

    app = s.web.app([('/', {'get': handler})])
    with s.web.test(app) as url:
        s.async.run_sync(lambda: main(url))


def test_get_params():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        raise tornado.gen.Return({'body': request['query']})

    @tornado.gen.coroutine
    def main(url):
        resp = yield s.web.get(url, query={'foo': 'bar'})
        assert resp['body'] == {'foo': 'bar'}

    app = s.web.app([('/', {'get': handler})])
    with s.web.test(app) as url:
        s.async.run_sync(lambda: main(url))


def test_post():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        raise tornado.gen.Return({'code': request['body']['num'] + 1})

    @tornado.gen.coroutine
    def main(url):
        resp = yield s.web.post(url, {'num': 200})
        assert resp['code'] == 201

    app = s.web.app([('/', {'post': handler})])
    with s.web.test(app) as url:
        s.async.run_sync(lambda: main(url))


def test_post_timeout():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.sleep(1)
        raise tornado.gen.Return({'code': 200})

    @tornado.gen.coroutine
    def main(url):
        resp = yield s.web.post(url, '', timeout=.001)
        assert resp['code'] == 201

    app = s.web.app([('/', {'post': handler})])
    with s.web.test(app) as url:
        with pytest.raises(s.web.Timeout):
            s.async.run_sync(lambda: main(url))


def test_basic():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        assert request['verb'] == 'get'
        raise tornado.gen.Return({'headers': {'foo': 'bar'},
                                  'code': 200,
                                  'body': 'ok'})
    app = s.web.app([('/', {'get': handler})])
    with s.web.test(app) as url:
        resp = s.web.get_sync(url)
        assert resp['body'] == 'ok'
        assert resp['headers']['foo'] == 'bar'


def test_middleware():
    def middleware(old_handler):
        @tornado.gen.coroutine
        def new_handler(request):
            request = s.dicts.merge(request, {'headers': {'asdf': ' [mod req]'}})
            response = yield old_handler(request)
            response = s.dicts.merge(response, {'body': response['body'] + ' [mod resp]'})
            raise tornado.gen.Return(response)
        return new_handler
    @middleware
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        raise tornado.gen.Return({'headers': {'foo': 'bar'},
                                  'code': 200,
                                  'body': 'ok' + request['headers']['asdf']})
    app = s.web.app([('/', {'get': handler})])
    with s.web.test(app) as url:
        resp = s.web.get_sync(url)
        assert resp['body'] == 'ok [mod req] [mod resp]'


def test_url_params():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        raise tornado.gen.Return({'code': 200,
                                  'body': request['query']})
    app = s.web.app([('/', {'get': handler})])
    with s.web.test(app) as url:
        resp = s.web.get_sync(url + '/?asdf=123&foo=bar&foo=notbar&stuff')
        assert resp['body'] == {'asdf': 123,
                                'foo': ['bar', 'notbar'],
                                'stuff': ''}


def test_url_args():
    @tornado.gen.coroutine
    def handler(request):
        yield tornado.gen.moment
        raise tornado.gen.Return({'code': 200,
                                  'body': {'foo': request['args']['foo']}})
    app = s.web.app([('/:foo/stuff', {'get': handler})])
    with s.web.test(app) as url:
        resp = s.web.get_sync(url + '/something/stuff')
        assert resp['body'] == {'foo': 'something'}, resp
