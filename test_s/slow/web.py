from __future__ import print_function
import s
import requests


def test1():
    def handler(request):
        assert request['verb'] == 'get'
        return {'headers': {'foo': 'bar'},
                'code': 200,
                'body': 'ok'}
    app = s.web.server([('/', {'GET': handler})])
    url, proc = s.web.test(app)
    resp = requests.get(url)
    assert resp.text == 'ok'
    assert resp.headers['foo'] == 'bar'
    proc.terminate()
