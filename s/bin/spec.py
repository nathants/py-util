from __future__ import print_function, absolute_import
import s
import os
import yaml
import json
import argh


class schemas:
    item = {'request': {'route': (':optional', str, '/'),
                        'verb': (':optional', (':or', 'get', 'post'), 'get'),
                        'body': (':optional', str, ''),
                        'https': (':optional', bool, False)},

            'response': {'code': (':optional', int, 200),
                         'body': (':optional', str, '')}}

    data = (':or', [item], {str: [item]}, {str: {str: [item]}})


def main():
    argh.dispatch_command(_main)


def _main(conf_path, cmd='', stream=False):
    """

    if request routes dont start with http, get host from cmd.

    if cmd, will be _run like $($cmd --port <port>)
    where <port> is chosen randomly and host is 0.0.0.0:<port>

    """

    with open(os.path.expanduser(conf_path)) as f:
        data = yaml.safe_load(f)
    data = s.schema.validate(schemas.data, data)

    if cmd:
        port = s.net.free_port()
        proc = s.proc.new(s.shell.run, cmd, '--port', port, stream=stream)

    print('spec: {conf_path}\n'.format(**locals()))

    if s.schema.is_valid([schemas.item], data):
        for item in data:
            text = _run(item, port)
            print(text)

    elif s.schema.is_valid({str: [schemas.item]}, data):
        for k, v in data.items():
            if cmd:
                proc.terminate()
                port = s.net.free_port()
                proc = s.proc.new(s.shell.run, cmd, '--port', port, stream=stream)
            for item in v:
                print(k)
                text = _run(item, port)
                print(s.strings.indent(text, 1))

    elif s.schema.is_valid({str: {str: [schemas.item]}}, data):
        for k1, v1 in data.items():
            print(k1)
            for k2, v2 in v1.items():
                for item in v2:
                    if cmd:
                        proc.terminate()
                        port = s.net.free_port()
                        proc = s.proc.new(s.shell.run, cmd, '--port', port, stream=stream)
                        s.web.wait_for_200('http://0.0.0.0:{port}'.format(**locals()))
                        import time
                        time.sleep(.5)
                    print('', k2)
                    text = _run(item, port)
                    print(s.strings.indent(text, 2))


@s.schema.check(schemas.item, (':maybe', int), _return=str)
def _run(item, port):
    host = '0.0.0.0:{port}'.format(**locals())
    func_name = '{verb}_sync'.format(**item['request'])
    route = item['request']['route']
    if not route.startswith('http'):
        protocol = 'https://' if item['request']['https'] else 'http://'
        url = protocol + host + route
    else:
        url = item['request']['route']
        assert url.startswith('http'), url
    body = item['request']['body']
    if not s.schema.is_valid(str, body):
        body = json.dumps(body)
    response = getattr(s.web, func_name)(url, *[body] if body else [])
    for k, v1 in item['response'].items():
        if k == 'body' and not v1:
            continue
        v2 = response[k]
        assert v1 == v2, 'excepted {k}={v1}, but got {k}={v2}'.format(**locals())
    return ':ok'
