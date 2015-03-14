from __future__ import print_function, absolute_import
import argh
import s.colors
import s.schema
import s.shell
import re
import os


def main():
    argh.dispatch_command(_main)


_path_skips = re.compile(r'\.egg|\.tox|\.git|__pycache__').search


_file_includes = re.compile(r'\.py$|\.yml$|\.yaml$').search


_schema = [(str, [(str, int)])]


_ljust_offset = 2


def _main(tree=False):
    with s.shell.climb_git_root():
        if tree:
            _tree()
        else:
            _sorted()


def _sorted():
    data = _tree_data()
    total = _total(data)
    data = [{'file': os.path.join(path.strip(), name.strip()),
             'loc': loc}
            for path, vals in data
            for name, loc in vals]
    data = sorted(data, key=lambda x: x['loc'], reverse=True)
    size = max(len(x['file']) for x in data) + _ljust_offset
    s.shell.less('\n'.join([s.colors.yellow('total: {}'.format(total))] +
                           [s.colors.blue(x['file'].ljust(size)) +
                            s.colors.red(x['loc'])
                            for x in data]))


def _tree():
    _tree_print(_tree_data())


def _total(data):
    return sum(loc
               for _, vals in data
               for _, loc in vals)


@s.schema.check(_return=_schema)
def _tree_data():
    data = []
    base = os.getcwd()
    for path, dirs, files in s.shell.walk():
        if not _path_skips(path):
            short_path = path.split(base)[1].lstrip('/')
            depth = len(short_path.split('/')) - 1
            offset = ' ' * depth
            data.append([offset + short_path or '.', []])
            for file_name in files:
                if _file_includes(file_name):
                    with s.shell.cd(path):
                        lines = open(file_name).read().splitlines()
                        lines = [x for x in lines
                                 if x.strip()
                                 and not x.strip().startswith('#')]
                    data[-1][-1].append([' ' + offset + file_name, len(lines)])
    return data


def _tree_print(data):
    lines = [s.colors.yellow('total: {}'.format(_total(data)))]
    for path, files in data:
        lines.append('')
        lines.append(s.colors.green(path))
        size = max(len(x) for x, _ in files) + _ljust_offset
        for name, loc in sorted(files, key=lambda x: x[0]):
            lines.append(s.colors.blue(name.ljust(size)) +
                         s.colors.red(loc))
    s.shell.less('\n'.join(lines))
