import argh
import s
import uuid
import os


def test_spec():
    with s.shell.cd(os.path.dirname(__file__)):
        port = s.net.free_port()
        proc = s.shell.run('python ./spec.py --port {port}'.format(**locals()), popen=True)
        s.shell.run('spec ./spec.yml --host "http://localhost:{port}"'.format(**locals()), stream=True)
        proc.terminate()


def main(port=8888):
    @s.async.coroutine
    def root(request):
        yield s.async.moment
        raise s.async.Return({'body': 'asdf'})

    _state = {}

    @s.async.coroutine
    def set(request):
        yield s.async.moment
        _state[request['args']['key']] = request['body']
        raise s.async.Return({'code': 200})

    @s.async.coroutine
    def get(request):
        yield s.async.moment
        try:
            raise s.async.Return({'body': _state[request['args']['key']]})
        except KeyError:
            raise s.async.Return({'code': 404})

    @s.async.coroutine
    def put(request):
        yield s.async.moment
        id = str(uuid.uuid4())
        _state[id] = request['body']
        if 'return_dict' in request['query']:
            raise s.async.Return({'body': {'uuid': id}})
        else:
            raise s.async.Return({'body': id})

    @s.async.coroutine
    def fetch(request):
        yield s.async.moment
        try:
            raise s.async.Return({'body': _state[request['args']['id']]})
        except KeyError:
            raise s.async.Return({'code': 404})

    @s.async.coroutine
    def reset(request):
        yield s.async.moment
        for k in _state:
            _state.pop(k)
        raise s.async.Return({'code': 200})

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
    s.async.ioloop().start()


if __name__ == '__main__':
    argh.dispatch_command(main)
