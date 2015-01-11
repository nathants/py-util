import argh
import s
import uuid


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
    raise s.async.Return({'body': id})


@s.async.coroutine
def fetch(request):
    yield s.async.moment
    try:
        raise s.async.Return({'body': _state[request['args']['id']]})
    except KeyError:
        raise s.async.Return({'code': 404})


def main(port=8888):
    s.log.setup()
    routes = [
        ('/', {'get': root}),
        ('/set/:key', {'post': set}),
        ('/get/:key', {'get': get}),
        ('/put', {'post': put}),
        ('/fetch/:id', {'get': fetch}),
    ]
    s.web.app(routes, debug=True).listen(port)
    s.async.ioloop().start()


if __name__ == '__main__':
    argh.dispatch_command(main)
