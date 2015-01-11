from __future__ import print_function, absolute_import
import logging
import s
import os
import yaml
import json
import argh
import atexit


class schemas:
    item = {'req': {'route': (':optional', str, '/'),
                    'verb': (':optional', (':or', 'get', 'post'), 'get'),
                    'body': (':optional', str, ''),
                    'https': (':optional', bool, False)},

            'rep': {'code': (':optional', int, 200),
                    'body': (':optional', (':or', str, {'$var': str}, {'var': str}), '')}}

    data = (':or', [item], {str: [item]}, {str: {str: [item]}})


def main():
    argh.dispatch_command(_main)


_state = {'port': None,
          'proc': None,
          'vars': {}}


@atexit.register
def kill_proc():
    if _state['proc']:
        _state['proc'].terminate()


def _restart_if_cmd():
    if _state['cmd']:
        logging.debug('restart: {cmd}'.format(**_state))
        _state['port'] = s.net.free_port()
        if _state['proc']:
            _state['proc'].terminate()
        _state['proc'] = s.shell.run(_state['cmd'], '--port', _state['port'], stream=_state['stream'], popen=True)
        s.web.wait_for_http('http://0.0.0.0:{port}'.format(**_state))


def _main(conf_path, cmd='', stream=False, filter=None):
    _state['stream'] = stream
    _state['cmd'] = cmd

    with open(os.path.expanduser(conf_path)) as f:
        data = yaml.safe_load(f)
    data = s.schema.validate(schemas.data, data)

    _restart_if_cmd()

    print('spec: {conf_path}'.format(**locals()))

    if s.schema.is_valid([schemas.item], data):
        for item in data:
            print(_run(item))

    elif s.schema.is_valid({str: [schemas.item]}, data):
        for k, v in data.items():
            if not filter or filter in k:
                print(k)
                _restart_if_cmd()
                for item in v:
                    print(s.strings.indent(_run(item), 1))

    elif s.schema.is_valid({str: {str: [schemas.item]}}, data):
        for k1, v1 in data.items():
            print('\n' + s.colors.blue(k1))
            for k2, v2 in v1.items():
                if not filter or any(filter in x for x in [k1, k2]):
                    _restart_if_cmd()
                    print('\n', s.colors.yellow(k2))
                    for i, item in enumerate(v2):
                        print('  {} '.format(i + 1), end='')
                        try:
                            _run(item)
                        except:
                            print(s.colors.red(' :error\n'))
                            text = '\nfailed in $red({}.{}) item number $red({})'.format(k1, k2, i + 1)
                            with s.exceptions.update(s.strings.color(text)):
                                raise


@s.schema.check(schemas.item)
def _run(item):
    func_name = '{verb}_sync'.format(**item['req'])
    route = item['req']['route']
    if not route.startswith('http'):
        protocol = 'https://' if item['req']['https'] else 'http://'
        host = '0.0.0.0:{port}'.format(**_state)
        url = protocol + host + route
    else:
        url = item['req']['route']
        assert url.startswith('http'), url
    url = '/'.join(_state['vars'][x[1:]]
                   if x.startswith('$')
                   else x
                   for x in url.split('/'))
    body = item['req']['body']
    if not s.schema.is_valid(str, body):
        body = json.dumps(body)
    with s.exceptions.update('\nverb={func_name}, url={url}, body={body}'.format(**locals())):
        print(s.colors.cyan(item['req']['verb']), url, end='')
        rep = getattr(s.web, func_name)(url, *[body] if body else [])
        for k, v1 in item['rep'].items():
            if k == 'body':
                if not v1:
                    continue
                elif s.schema.is_valid({'$var': str}, v1):
                    _state['vars'][v1['$var']] = rep[k]
                    continue
            v2 = rep[k]
            if s.schema.is_valid({'var': str}, v1):
                v1 = _state['vars'][v1['var']]
            assert v1 == v2, 'excepted {k}={v1}, but got {k}={v2}'.format(**locals())
    print(s.colors.green(' :ok'))
