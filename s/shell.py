from __future__ import print_function
import subprocess
import contextlib
import os
import s
import logging
import collections
import random
import string
import time


_state = {}


def _set_state(key):
    @contextlib.contextmanager
    def fn():
        orig = _state.get(key)
        _state[key] = True
        try:
            yield
        except:
            raise
        finally:
            del _state[key]
            if orig is not None:
                _state[key] = orig
    return fn


set_stream = _set_state('stream')


_interactive_fn = {True: subprocess.check_call, False: subprocess.call}


_call_kw = {'shell': True, 'executable': '/bin/bash'}


def _readlines(proc, *callbacks):
    lines = []
    def cb(line):
        line = s.hacks.stringify(line)
        if line.strip():
            for callback in callbacks:
                callback(line)
            lines.append(line)
    while proc.poll() is None:
        cb(proc.stdout.readline().rstrip())
    for line in proc.communicate()[0].strip().splitlines(): # sometimes the last line disappears, especially when there is very little stdout
        cb(line.rstrip())
    if len(lines) == 1:
        lines = lines[:1]
    return '\n'.join(lines)


def run(*a, **kw):
    interactive = kw.pop('interactive', False)
    warn = kw.pop('warn', False)
    stream = kw.pop('stream', _state.get('stream', False))
    def logging_cb(x):
        if stream:
            if logging.root.handlers:
                logging.info(x)
            else:
                print(x)
    user_cb = kw.pop('callback', lambda x: None)
    cmd = ' '.join(a)
    logging_cb('[{}] [{}]'.format(cmd, os.getcwd()))
    if interactive:
        _interactive_fn[warn](cmd, **_call_kw)
    else:
        proc = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, **_call_kw)
        output = _readlines(proc, logging_cb, user_cb)
        if warn:
            logging_cb('exit-code={} from cmd: {}'.format(proc.returncode, cmd))
            return collections.namedtuple('output', 'output exitcode')(output, proc.returncode)
        elif proc.returncode != 0:
            output = output if not stream else ''
            raise Exception('{}\nexitcode={} from cmd: {}, cwd: {}'.format(output, proc.returncode, cmd, os.getcwd()))
        return output


def listdir(path='.', abs=False):
    return list_filtered(path, abs, lambda *a: True)


def dirs(path='.', abs=False):
    return list_filtered(path, abs, os.path.isdir)


def files(path='.', abs=False):
    return list_filtered(path, abs, os.path.isfile)


def list_filtered(path, abs, predicate):
    path = os.path.expanduser(path)
    resolve = lambda x: os.path.abspath(os.path.join(path, x))
    return [resolve(x) if abs else x
            for x in sorted(os.listdir(path))
            if predicate(os.path.join(path, x))]


@contextlib.contextmanager
def climb_git_root(where='.'):
    with cd(where):
        while True:
            assert os.getcwd() != '/', 'didnt find .git climbing from: {}'.format(os.getcwd())
            if '.git' in s.shell.dirs():
                break
            os.chdir('..')
        yield


@contextlib.contextmanager
def cd(path='.'):
    orig = os.path.abspath(os.getcwd())
    if path:
        path = os.path.expanduser(path)
        if not os.path.isdir(path):
            run('mkdir -p', path)
        os.chdir(path)
    try:
        yield
    except:
        raise
    finally:
        os.chdir(orig)


@contextlib.contextmanager
def tempdir(cleanup=True, intemp=True):
    while True:
        try:
            letters = string.letters
        except AttributeError:
            letters = string.ascii_letters
        path = ''.join(random.choice(letters) for _ in range(20))
        path = '/tmp/{}'.format(path) if intemp else path
        if not os.path.exists(path):
            break
    run('mkdir', path)
    if not cleanup and intemp:
        path = os.path.basename(path)
        cmd = "python -c 'import time; assert {} + 60 * 60 * 72 < time.time()' && sudo rm -rf /tmp/{}".format(time.time(), path)
        when = '{} * * * *'.format(random.randint(0, 59))
        cron(path, when, cmd, selfdestruct=True)
    try:
        with cd(path):
            yield path
    except:
        raise
    finally:
        if cleanup:
            run('sudo rm -rf', path)


def cron(name, when, cmd, user='root', selfdestruct=False):
    if os.path.isdir('/etc/cron.d'):
        return
    assert name not in os.listdir('/etc/cron.d'), '"{}" already exists in /etc/cron.d'.format(name)
    name = '/etc/cron.d/{}'.format(name)
    if selfdestruct:
        cmd += ' && sudo rm -f {}'.format(name)
    run('sudo rm -f /tmp/test.sh')
    with open('/tmp/test.sh', 'w') as file:
        file.write(cmd)
    try:
        run('sh -n /tmp/test.sh')
    except:
        raise Exception('cmd is invalid: {}'.format(cmd))
    run('sudo touch', name)
    run('sudo chmod ugo+rw', name)
    with open(name, 'w') as file:
        file.write('{when} {user} {cmd}\n'.format(**locals()))
    run('sudo chmod 644', name)
