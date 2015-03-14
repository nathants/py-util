from __future__ import print_function, absolute_import
import yaml
import s.schema
import s.dicts
import s.web
import s.colors
import s.strings
import s.exceptions
import os
import json
import argh


# TODO how to deal with many apps/ports, ie fig up?


class schemas:
    _verbs = (':or', 'get', 'post')

    _body = (':or', str, {'$set': str}, {'$get': str})

    item = {'info': (':optional', str, ''),
            'req': {'route': (':optional', str, '/'),
                    'verb': (':optional', _verbs, 'get'),
                    'body': (':optional', _body, ''),
                    'https': (':optional', bool, False)},

            'rep': {'code': (':optional', int, 200),
                    'body': (':optional', _body, '')}}

    data = {str: {str: [item]}}


def main():
    argh.dispatch_command(_main)


_state = {'port': None,
          'proc': None,
          'vars': None,
          'host': None}


def _reset():
    s.web.post_sync(_state['host'] + '/_reset', '')


def _main(conf_path, host='', cmd='', stream=False, filter=None):
    _state['stream'] = stream
    _state['cmd'] = cmd
    _state['host'] = host.rstrip('/')

    with open(os.path.expanduser(conf_path)) as f:
        data = yaml.safe_load(f)
    data = s.schema.validate(schemas.data, data)

    _reset()

    print('spec: {conf_path}'.format(**locals()))

    for k1, v in data.items():
        print('\n' + s.colors.blue(k1))
        for k2, rep_v in v.items():
            if not filter or any(filter in x for x in [k1, k2]):
                _state['vars'] = {}
                _reset()
                print('\n' + s.strings.indent(s.colors.yellow(k2), 1))
                for i, item in enumerate(rep_v):
                    _process(i, item)


def _process(i, item):
    if item.get('info'):
        print(s.strings.indent(s.colors.white('{info}'.format(**item)), 2))
    print(s.strings.indent('{} '.format(i + 1), 3 if item.get('info') else 2), end='')
    try:
        _run(item)
    except:
        print(s.colors.red(' :error\n'))
        text = _format(s.dicts.drop(item, 'info'))
        print(s.colors.red(s.strings.indent(text, 2)) + '\n')
        raise
    if item.get('info'):
        print('')


def _format(x):
    return yaml.safe_dump(json.loads(json.dumps(x)), default_flow_style=False)


def _get_url(item):
    route = item['req']['route']
    if route.startswith('http'):
        url = item['req']['route']
    elif _state.get('host'):
        url = _state['host'] + route
    else:
        protocol = 'https://' if item['req']['https'] else 'http://'
        host = '0.0.0.0:{port}'.format(**_state)
        url = protocol + host + route
    assert url.startswith('http'), url
    url = '/'.join(s.dicts.get(_state, ['vars'] + x[1:].split('.'))
                   if x.startswith('$')
                   else x
                   for x in url.split('/'))
    return url


def _get_body(item):
    body = item['req']['body']
    if s.schema.is_valid({'$get': str}, body):
        body = s.dicts.get(_state, ['vars'] + body['$get'].split('.'))
    if not s.schema.is_valid(str, body):
        body = json.dumps(body)
    return body


@s.schema.check(schemas.item)
def _run(item):
    verb = item['req']['verb']
    func_name = '{verb}_sync'.format(**locals())
    url = _get_url(item)
    body = _get_body(item)
    print(s.colors.cyan(item['req']['verb'].ljust(4)), url, end='')
    with s.exceptions.update('\nverb={verb}, url={url}, body={body}'.format(**locals())):
        rep = getattr(s.web, func_name)(url, *[body] if body else [])
        for k, v in item['rep'].items():
            _check_rep(k, v, rep)
    print(s.colors.green(' :ok'))


def _check_rep(k, v, rep):
    if k == 'body':
        if not v:
            return
        elif s.schema.is_valid({'$set': str}, v):
            _state['vars'][v['$set']] = rep[k]
            return
    rep_v = rep[k]
    if s.schema.is_valid({'$get': str}, v):
        v = s.dicts.get(_state, ['vars'] + v['$get'].split('.'))
    assert v == rep_v, 'response expected {k}={v}, but got {k}={rep_v}'.format(**locals())
