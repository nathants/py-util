from __future__ import print_function, absolute_import
import s
import requests
import json


def test_basic():
    def handler(request):
        assert request['verb'] == 'get'
        return {'headers': {'foo': 'bar'},
                'code': 200,
                'body': 'ok'}
    app = s.web.server([('/', {'GET': handler})])
    with s.web.test(app) as url:
        resp = requests.get(url)
        assert resp.text == 'ok'
        assert resp.headers['foo'] == 'bar'


def test_url_params():
    def handler(request):
        return {'code': 200,
                'body': json.dumps(request['query'])}
    app = s.web.server([('/', {'GET': handler})])
    with s.web.test(app) as url:
        resp = requests.get(url + '?asdf=123&foo=bar&foo=notbar&stuff')
        assert resp.json() == {'asdf': '123',
                               'foo': ['bar', 'notbar'],
                               'stuff': ''}


def test_url_args():
    def handler(request):
        return {'code': 200,
                'body': json.dumps({'foo': request['arguments']['foo']})}
    app = s.web.server([('/:foo/stuff', {'GET': handler})])
    with s.web.test(app) as url:
        resp = requests.get(url + 'something/stuff')
        assert resp.json() == {'foo': 'something'}
