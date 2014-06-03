from __future__ import absolute_import, print_function
import subprocess
import contextlib
import os
import s
import collections
import random
import string
import time
import argh
import types


# todo use https://pypi.python.org/pypi/subprocess32/ on python2.7


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


def _logging_cb(stream):
    def fn(x):
        if stream:
            if hasattr(s.log.setup, s.cached._attr):
                s.log.info(x)
            else:
                print(x)
    return fn


_interactive_fn = {False: subprocess.check_call, True: subprocess.call}


_call_kw = {'shell': True, 'executable': '/bin/bash'}


def run(*a, **kw):
    interactive = kw.pop('interactive', False)
    warn = kw.pop('warn', False)
    stream = kw.pop('stream', _state.get('stream', False))
    logging_cb = _logging_cb(stream)
    user_cb = kw.pop('callback', lambda x: None)
    cmd = ' '.join(a)
    logging_cb('$({}) [cwd={}]'.format(s.colors.yellow(cmd), os.getcwd()))
    if interactive:
        _interactive_fn[warn](cmd, **_call_kw)
    else:
        proc = subprocess.Popen(cmd, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, **_call_kw)
        output = _readlines(proc, logging_cb, user_cb)
        if warn:
            logging_cb('exit-code={} from cmd: {}'.format(proc.returncode, cmd))
            return collections.namedtuple('shell_output', 'output exitcode')(output, proc.returncode)
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


def git_root(where='.'):
    with climb_git_root(where):
        return os.getcwd()



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
    run('mkdir -p', path)
    if not cleanup and intemp:
        path = os.path.basename(path)
        cron_rm_path_later(path, hours=24)
    try:
        with cd(path):
            yield path
    except:
        raise
    finally:
        if cleanup:
            run('sudo rm -rf', path)


def cron_rm_path_later(path, hours):
    cmd = "python -c 'import time; assert {} + 60 * 60 * {}  < time.time()' && sudo rm -rf /tmp/{}".format(time.time(), hours, path)
    when = '{} * * * *'.format(random.randint(0, 59))
    cron(path, when, cmd, selfdestruct=True)


def cron(name, when, cmd, user='root', selfdestruct=False):
    if os.path.isdir('/etc/cron.d'):
        return
    assert name not in os.listdir('/etc/cron.d'), '"{}" already exists in /etc/cron.d'.format(name)
    name = '/etc/cron.d/{}'.format(name)
    if selfdestruct:
        cmd += ' && sudo rm -f {}'.format(name)
    run('sudo rm -f /tmp/tmp.sh')
    with open('/tmp/tmp.sh', 'w') as file:
        file.write(cmd)
    if run('sh -n /tmp/tmp.sh', warn=True).exitcode != 0:
        raise Exception('cmd is invalid: {}'.format(cmd))
    run('sudo touch', name)
    run('sudo chmod ugo+rw', name)
    with open(name, 'w') as file:
        file.write('{when} {user} {cmd}\n'.format(**locals()))
    run('sudo chmod 644', name)


def walk_files_mtime(directories=['.'], predicate=lambda filepath: True):
    return [(os.path.join(path, f), os.stat(os.path.join(path, f)).st_mtime)
            for d in directories
            for path, _, files in os.walk(d)
            for f in files
            if predicate(os.path.join(path, f))
            and not f.startswith('.')]


def dispatch_commands(_globals, _name_):
    argh.dispatch_commands(sorted([
        v for k, v in _globals.items()
        if type(v) == types.FunctionType
        and v.__module__ == _name_
        and not k.startswith('_')
    ], key=lambda x: x.__name__))


def climb(where='.'):
    val = []
    with s.shell.cd(where):
        while True:
            val.append([os.getcwd(), s.shell.dirs(), s.shell.files()])
            if os.getcwd() == '/':
                break
            os.chdir('..')
    return val


def walk(where='.'):
    with s.shell.cd(where):
        return [(os.path.abspath(path), dirs, files)
                for path, dirs, files in os.walk('.')]


def module_name(filepath):
    assert os.path.isfile(filepath), 'not a file: {}'.format(filepath)
    climb_data = climb(os.path.dirname(filepath))
    return _module_name(filepath, climb_data)


def _module_name(filepath, climb_data):
    for i, (path, _, files) in enumerate(climb_data, 1):
        if '__init__.py' not in files:
            break
    filepath = filepath.replace('.pyc', '').replace('.py', '')
    parts = filepath.split('/')[-i:]
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)
