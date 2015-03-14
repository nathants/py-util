from __future__ import print_function, absolute_import
import argh
import tornado.gen
import tornado.ioloop
import s.net
import s.log
import s.web
import s.shell
import uuid
import os


def test_spec():
    with s.shell.cd(os.path.dirname(__file__)):
        port = s.net.free_port()
        proc = s.shell.run('python ./spec.py --port {port}'.format(**locals()), popen=True)
        url = 'http://localhost:{port}'.format(**locals())
        s.web.wait_for_http(url)
        s.shell.run('spec ./spec.yml --host {url}'.format(**locals()), stream=True)
        proc.terminate()


def main(port=8888):
    @tornado.gen.coroutine
    def root(request):
        yield tornado.gen.moment
        raise tornado.gen.Return({'body': 'asdf'})

    _state = {}

    @tornado.gen.coroutine
    def set(request):
        yield tornado.gen.moment
        _state[request['args']['key']] = request['body']
        raise tornado.gen.Return({'code': 200})

    @tornado.gen.coroutine
    def get(request):
        yield tornado.gen.moment
        try:
            raise tornado.gen.Return({'body': _state[request['args']['key']]})
        except KeyError:
            raise tornado.gen.Return({'code': 404})

    @tornado.gen.coroutine
    def put(request):
        yield tornado.gen.moment
        id = str(uuid.uuid4())
        _state[id] = request['body']
        if 'return_dict' in request['query']:
            raise tornado.gen.Return({'body': {'uuid': id}})
        else:
            raise tornado.gen.Return({'body': id})

    @tornado.gen.coroutine
    def fetch(request):
        yield tornado.gen.moment
        try:
            raise tornado.gen.Return({'body': _state[request['args']['id']]})
        except KeyError:
            raise tornado.gen.Return({'code': 404})

    @tornado.gen.coroutine
    def reset(request):
        yield tornado.gen.moment
        for k in _state:
            _state.pop(k)
        raise tornado.gen.Return({'code': 200})

    s.log.setup()
    routes = [
        ('/', {'get': root}),
        ('/set/:key', {'post': set}),
        ('/get/:key', {'get': get}),
        ('/put', {'post': put}),
        ('/fetch/:id', {'get': fetch}),
        ('/_reset', {'post': reset}),
    ]
    s.web.app(routes, debug=True).listen(port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == '__main__':
    argh.dispatch_command(main)
