import yaml
import re
import itertools
import sys
import argh
import s.shell
import s.exceptions
import s.colors
import s.dicts
import s.net
import s.web
import os


class schemas:
    data = {}


_services = './docker/state/services.yml'


@argh.arg('cmd', nargs='?', default=None)
@argh.arg('-a', '--append-to-cmd')
@argh.arg('-ncb', '--no-clean-before')
@argh.arg('-nca', '--no-clean-after')
def run(action_name, cmd, append_to_cmd=None, tty=False, no_clean_before=False, no_clean_after=False):
    """run an action"""
    build(action_name)
    tty = True if cmd == 'bash' else tty
    action = _get_action(action_name)
    if not no_clean_before:
        stop(action_name)
    try:
        _start_deps(action)
        ports(action_name)
        if 'main' in action:
            print('start main')
            try:
                s.shell.run(_run_cmd(action['main'], tty, cmd, append_to_cmd), interactive=True)
            except:
                sys.exit(1)
    finally:
        if not no_clean_after:
            stop(action_name)


def logs(action_name, container_name=None):
    action = _get_action(action_name)
    if container_name:
        1/0 # FIXME
    else:
        procs = []
        for container_name, data in action.items():
            print(container_name)
            procs.append(s.proc.new(s.shell.run, 'docker logs -f', container_name, stream=True))
        for p in procs:
            p.join()


def ports(action_name, container_name=None):
    action = _get_action(action_name)
    if container_name:
        1/0 # FIXME
    else:
        for container_name, data in action.items():
            try:
                ports = _exposed_ports(data['tag'])
            except:
                continue
            else:
                print('')
                print(container_name)
                for port in sorted(ports, key=lambda x: x['internal']):
                    print(' http://localhost:%(external)s -> docker:%(internal)s' % port)
                print('')


def stop(action_name):
    action = _get_action(action_name)
    for container_name, data in action.items():
        with s.exceptions.ignore():
            s.shell.run('sudo docker kill', data['tag'])
            s.shell.run('sudo docker rm', data['tag'])


def build(action_name, container=None, nocache=False, pull=False, force=False):
    """build an actions containers"""
    action = _get_action(action_name)
    for container_name, data in action.items():
        if not container or container_name == container:
            if force or not s.shell.run('sudo docker inspect', data['tag'], zero=True, stream=False):
                s.shell.run(_build_cmd(data, nocache, pull), stream=True)
                print(s.colors.green('built:'), data['tag'])


def show():
    """show available actions"""
    data = _get_actions()
    for action_name in sorted(data):
        print('')
        print(action_name)
        for container in data[action_name]:
            print('', container)


def main():
    assert os.path.isdir('docker'), 'must have a dir: ./docker'
    assert os.path.isfile('system.yml'), 'must have a file: ./system.yml'
    if s.shell.override('--stream'):
        with s.shell.set_stream():
            _main()
    else:
        _main()


def _main():
    s.shell.run('mkdir -p ./docker/state')
    s.shell.dispatch_commands(globals(), __name__)


def _exposed_ports(tag):
    return [s.dicts.map(lambda k, v: [k, int(v)],
                        re.search(r'(?P<internal>\d+).*-> 0.0.0.0:(?P<external>\d+)', x).groupdict())
            for x in s.shell.run('sudo docker port', tag).splitlines()]


def _start_deps(action):
    s.shell.run('rm -f', _services)
    to_start = list(s.dicts.drop(action, 'main').items())
    if to_start:
        started = []
        for i in itertools.count():
            container_name, data = to_start.pop(0)
            deps = data.get('depends', [])
            if not deps or all(x in started for x in deps):
                # TODO supervise this process
                s.shell.run(_run_cmd(data, bg=True))
                started.append(container_name)
                ports = _exposed_ports(data['tag'])
                if len(ports) == 1:
                    data = {'port': ports[0]['external'],
                            'host': _host_ip()}
                    with open(_services, 'a') as f:
                        f.write(yaml.dump({container_name: data}))
                elif len(ports) > 1:
                    data = {'ports': {port['internal']: port['external'] for port in ports},
                            'host': _host_ip()}
                    with open(_services, 'a') as f:
                        f.write(yaml.dump({container_name: data}))
                # s.web.wait_for_http('http://{host}:{port}'.format(**data))
            else:
                to_start.append([container_name, data])
            assert i < 1000, 'never resolved dependency order. remaining: {}'.format(to_start)
            if not to_start:
                return


def _tag_containers(action_name, action):
    for container_name, data in action.items():
        action[container_name]['tag'] = (action[container_name].get('image')
                                         or '_'.join([os.path.basename(os.getcwd()),
                                                      action_name,
                                                      container_name]))
    return action


def _get_actions():
    with open('./system.yml') as f:
        return yaml.safe_load(f)


def _get_action(action_name):
    action = _get_actions()[action_name]
    return _tag_containers(action_name, action)


def _build_cmd(data, nocache, pull):
    return ' '.join([
        'sudo docker build',
        '-t', data['tag'],
        '--force-rm=true',
        '-f ' + data['dockerfile'] if 'dockerfile' in data else '',
        '--no-cache=true' if nocache else '--no-cache=false',
        '--pull=true' if pull else '--pull=false',
        '.',
    ])


def _read_env(name):
    if not isinstance(name, str) or not name.startswith('$services.'):
        return name
    with open(_services) as f:
        keys = [int(x) if x.isdigit() else x
                for x in name.split('$services.')[-1].split('.')]
        return s.dicts.get(yaml.safe_load(f), keys)


def _run_cmd(data, tty=False, cmd=None, append_to_cmd=None, bg=False):
    append_to_cmd = append_to_cmd or ''
    return ' '.join(
        ['sudo docker run',
         '--publish-all=true',
         '-it' if tty else '',
         '-d' if bg else '',
         '--name={tag}'.format(**data),
         '--memory={memory}'.format(**data) if 'memory' in data else '',
         '-v {}/docker/state:/state'.format(os.getcwd())] +
        ['-v {}:{}'.format(os.path.abspath(os.path.expanduser(a)), b)
         for x in data.get('volumes', [])
         for y in [str(x).split(':')]
         for a, b in [(y + y)[:2]]] +
        ['--env {}={}'.format(k, _read_env(v)) for k, v in data.get('env', {}).items()] +
        ['-p {}:{}'.format(*z)
         for x in data.get('ports', [])
         for y in [str(x).split(':')]
         for z in [([s.net.free_port()] + y)[-2:]]] +
        [data['tag']] +
        ["bash -c '{} {}'".format(cmd, append_to_cmd)
         if cmd
         else "bash -c '{} {}'".format(data['cmd'], append_to_cmd)
         if 'cmd' in data
         else '']
    )


def _host_ip():
    val = s.shell.run('ifconfig docker0|grep "inet addr:"')
    val = val.split()[1].split(':')[-1]
    return val
