import argh
import s


@s.async.coroutine
def root(request):
    yield s.async.moment
    raise s.async.Return({'body': 'asdf'})

_state = {}


@s.async.coroutine
def set(request):
    yield s.async.moment
    _state[request['arguments']['key']] = request['body']
    raise s.async.Return({'code': 200})


@s.async.coroutine
def get(request):
    yield s.async.moment
    try:
        body = _state[request['arguments']['key']]
        raise s.async.Return({'body': body})
    except KeyError:
        raise s.async.Return({'code': 404})


def main(port=8888):
    s.log.setup()
    s.web.app(
        [
            ('/', {'get': root}),
            ('/set/:key', {'post': set}),
            ('/get/:key', {'get': get}),
        ],
        debug=True
    ).listen(port)
    s.async.ioloop().start()


if __name__ == '__main__':
    argh.dispatch_command(main)
