from __future__ import print_function, absolute_import
import os
import s
import argh
import sys
import six
import pager


@s.cached.func
def _repos():
    message = 'comma seperated directories to look for git repos in'
    search_dirs = s.shell.get_or_prompt_pref('search_dirs', __file__, message=message)
    search_dirs = [s.shell.abspand(x) for x in search_dirs.split(',')]
    return [repo
            for search_dir in search_dirs
            for repo in s.shell.dirs(search_dir, abs=True)
            if '.git' in s.shell.dirs(repo)]


def _commitable_paths():
    cmd = "git status -s -uall | grep -P '^ ?[MA\?]' | awk '{print $2}'"
    return s.shell.run(cmd).splitlines()


def _less(text):
    if text:
        with s.shell.tempdir():
            with open('_', 'w') as _file:
                _file.write(text + '\n\n')
            s.shell.run('less -cR _', interactive=True)


def _git_diff_cached_less(path):
    _less(s.shell.run('git -c color.ui=always diff --cached', path))


def _prompt_and_commit(path):
    msg = six.moves.input('\ncommit message: ')
    assert '"' not in msg and "'" not in msg, 'quotes in messages unsupported: {}'.format(msg)
    s.shell.run('git commit -n -m "{}"'.format(msg), stream=True)


def _git_reset_head():
    s.shell.run('git reset HEAD')


@argh.named('d')
def diff():
    """
    git diff for all files in the current repo
    """
    with s.shell.climb_git_root():
        _git_reset_head()
        paths = _commitable_paths()
        for path in paths:
            s.shell.run('git add', path)
            _git_diff_cached_less(path)
        _git_reset_head()


@argh.named('c')
def commit(skip_precommit=False):
    """
    git commit for all files in the current repo
    """
    with s.shell.climb_git_root():
        _git_reset_head()
        paths = _commitable_paths()
        if not paths:
            print('nothing to commit')
            sys.exit(1)
        else:
            pre_commit = '.git/hooks/pre-commit'
            if os.path.isfile(pre_commit) and not skip_precommit:
                if s.shell.run(pre_commit, stream=True, warn=True)['exitcode'] != 0:
                    sys.exit(1)
            _less('going to walk through these files:\n\n {}'.format('\n '.join(paths)))
            for path in paths:
                s.shell.run('git add', path)
                _git_diff_cached_less(path)
                print('[c]ommit, [s]kip, [p]atch ? ', end='')
                action = pager.getch()
                if action == 'c':
                    _prompt_and_commit(path)
                elif action == 's':
                    _git_reset_head()
                elif action == 'p':
                    while path in _commitable_paths():
                        s.shell.run('git reset HEAD', path)
                        s.shell.run('git add --patch', path, interactive=True)
                        _git_diff_cached_less(path)
                        print('[c]ommit, [s]kip, [p]atch ? ', end='')
                        action = pager.getch()
                        if action == 'c':
                            _prompt_and_commit(path)
                        elif action == 's':
                            _git_reset_head()
                else:
                    print('invalid choice:', action)
                    sys.exit(1)


@argh.named('s')
def status():
    """
    git status for all repos in your search_dirs
    """
    text = ''
    for repo in _repos():
        with s.shell.cd(repo):
            output = s.shell.run('git -c color.ui=always status -s')
            if output:
                text += s.strings.color('\n$red({repo})\n{output}\n'.format(**locals()))
    _less(text)


def main():
    s.shell.dispatch_commands(globals(), __name__)
