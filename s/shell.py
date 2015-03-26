from __future__ import absolute_import, print_function
import sys
import logging
import six
import yaml
import subprocess
import contextlib
import os
import s.colors
import s.hacks
import s.proc
import random
import string
import argh
import types


# TODO use https://pypi.python.org/pypi/subprocess32/ on python2.7


def _sudo():
    try:
        run('sudo whoami')
        return 'sudo'
    except:
        return ''


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


def _process_lines(proc, log, callback=None):
    lines = []
    def process(line):
        line = s.hacks.stringify(line).rstrip()
        if line.strip():
            log(line)
            lines.append(line)
        if callback:
            callback(line)
    while proc.poll() is None:
        process(proc.stdout.readline())
    for line in proc.communicate()[0].strip().splitlines(): # sometimes the last line disappears
        process(line)
    return '\n'.join(lines)


def _get_log_or_print(should_log):
    def fn(x):
        if should_log:
            # TODO this is dumb
            import s.log
            if hasattr(s.log.setup, '_cached_value'):
                logging.info(x)
            else:
                print(x)
    return fn


_interactive_func = {False: subprocess.check_call, True: subprocess.call}


_call_kw = {'shell': True, 'executable': '/bin/bash', 'stderr': subprocess.STDOUT}


def run(*a, **kw):
    interactive = kw.pop('interactive', False)
    warn = kw.pop('warn', False)
    zero = kw.pop('zero', False)
    echo = kw.pop('echo', False)
    callback = kw.pop('callback', None)
    stream = kw.pop('stream', _state.get('stream', False))
    popen = kw.pop('popen', False)
    log_or_print = _get_log_or_print(stream or echo)
    cmd = ' '.join(map(str, a))
    log_or_print('$({}) [cwd={}]'.format(s.colors.yellow(cmd), os.getcwd()))
    if interactive:
        _interactive_func[warn](cmd, **_call_kw)
    elif popen:
        return subprocess.Popen(cmd, stdout=subprocess.PIPE, **_call_kw)
    elif stream or warn or callback or zero:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, **_call_kw)
        output = _process_lines(proc, log_or_print, callback)
        if warn:
            log_or_print('exit-code={} from cmd: {}'.format(proc.returncode, cmd))
            return {'output': output, 'exitcode': proc.returncode, 'cmd': cmd}
        elif zero:
            return proc.returncode == 0
        elif proc.returncode != 0:
            output = '' if stream else output
            raise Exception('{}\nexitcode={} from cmd: {}, cwd: {}'.format(output, proc.returncode, cmd, os.getcwd()))
        return output
    else:
        return s.hacks.stringify(subprocess.check_output(cmd, **_call_kw).rstrip())


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
            if '.git' in dirs():
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
        path = os.path.join('/tmp', path) if intemp else path
        if not os.path.exists(path):
            break
    run('mkdir -p', path)
    try:
        with cd(path):
            yield path
    except:
        raise
    finally:
        if cleanup:
            run(_sudo(), 'rm -rf', path)


def cron(name, when, cmd, user='root', selfdestruct=False):
    # TODO use users crontabs dir instead of cron.d
    if not os.path.isdir('/etc/cron.d') or not _sudo():
        return
    assert name not in os.listdir('/etc/cron.d'), '"{}" already exists in /etc/cron.d'.format(name)
    name = '/etc/cron.d/{}'.format(name)
    if selfdestruct:
        cmd += ' && sudo rm -f {}'.format(name)
    run('sudo rm -f /tmp/tmp.sh')
    with open('/tmp/tmp.sh', 'w') as file:
        file.write(cmd)
    if run('sh -n /tmp/tmp.sh', warn=True)['exitcode'] != 0:
        raise Exception('cmd is invalid: {}'.format(cmd))
    run('sudo touch', name)
    run('sudo chmod ugo+rw', name)
    with open(name, 'w') as file:
        file.write('{when} {user} {cmd}\n'.format(**locals()))
    run('sudo chmod 644', name)


def walk_files(directories=['.'], predicate=lambda filepath: True):
    return [os.path.join(path, f)
            for d in directories
            for path, _, files in os.walk(d)
            for f in files
            if predicate(os.path.join(path, f))
            and not f.startswith('.')]


def dispatch_commands(_globals, _name_):
    argh.dispatch_commands(sorted([
        v for k, v in _globals.items()
        if isinstance(v, types.FunctionType)
        and v.__module__ == _name_
        and not k.startswith('_')
        and k != 'main'
    ], key=lambda x: x.__name__))


def climb(where='.'):
    val = []
    with cd(where):
        while True:
            val.append([os.getcwd(), dirs(), files()])
            if os.getcwd() == '/':
                break
            os.chdir('..')
    return val


def walk(where='.'):
    with cd(where):
        return [(os.path.abspath(path), dirs, files)
                for path, dirs, files in os.walk('.')]


def module_name(filepath):
    assert os.path.isfile(filepath), 'not a file: {}'.format(filepath)
    climb_data = climb(os.path.dirname(filepath))
    return _module_name(filepath, climb_data)


def rel_path(filepath):
    assert os.path.isfile(filepath), 'not a file: {}'.format(filepath)
    climb_data = climb(os.path.dirname(filepath))
    return _rel_path(filepath, climb_data)


def _rel_path(filepath, climb_data):
    for i, (path, _, files) in enumerate(climb_data, 1):
        if '__init__.py' not in files:
            break
    parts = filepath.split('/')[-i:]
    return '/'.join(parts)


def _module_name(filepath, climb_data):
    val = _rel_path(filepath, climb_data)
    val = val.replace('.pyc', '').replace('.py', '')
    parts = val.split('/')
    if parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


def _pref_path(_file_):
    _file_ = abspand(_file_)
    name = '.{}.{}.{}.yaml'.format(*map(os.path.basename, [
        os.path.dirname(os.path.dirname(_file_)),
        os.path.dirname(_file_),
        _file_.replace('.pyc', '').replace('.py', ''),
    ]))
    return os.path.join(os.environ['HOME'], name)


def get_or_prompt_pref(key, _file_, default=None, message=None):
    path = _pref_path(_file_)
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except IOError:
        data = {}

    try:
        return data[key]
    except KeyError:
        if message:
            print(message)
        default = 'or default: {}'.format(default) if default else ''
        data[key] = six.moves.input('value for {key} {default}? '.format(**locals()))
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        return data[key]


def abspand(path):
    return os.path.abspath(os.path.expanduser(path))


# def watch_files(route):
#     def watcher():
#         try:
#             with climb_git_root():
#                 while True:
#                     # TODO use tornado subprocess
#                     fifo = '/tmp/{}'.format(uuid.uuid4())
#                     cmd = ("(find -name '*.py' | entr -d +{fifo} &) &&"
#                            "sleep 1 &&" # TODO this should probably be smarter
#                            "while read F; do echo $F; done < {fifo}".format(**locals()))
#                     run(cmd, callback=lambda x: s.sock.push_sync(route, x))
#         except KeyboardInterrupt:
#             run("ps -eo pid,cmd|grep 'entr -d echo'|awk '{print $1}'|xargs kill")
#     s.proc.new(watcher)
#     return True


def override(flag):
    var = '_override_{}'.format(flag.strip('-'))
    if var in os.environ or flag in sys.argv:
        if flag in sys.argv:
            sys.argv.remove(flag)
        os.environ[var] = ''
        return True


def less(text):
    if text:
        with tempdir():
            with open('_', 'w') as f:
                f.write(text + '\n\n')
            run('less -cR _', interactive=True)
