from __future__ import print_function, absolute_import
import s
import argh


@s.cached.func
def repos():
    message = 'comma seperated directories to look for git repos in'
    search_dirs = s.shell.get_or_prompt_pref('search_dirs', __file__, message=message)
    search_dirs = [s.shell.expand(x) for x in search_dirs.split(',')]
    return [repo
            for search_dir in search_dirs
            for repo in s.shell.dirs(search_dir, abs=True)
            if '.git' in s.shell.dirs(repo)]


@argh.alias('s')
def status():
    text = ''
    for repo in repos():
        with s.shell.cd(repo):
            output = s.shell.run('git -c color.ui=always status -s')
            if output:
                text += s.strings.color('\n$red({repo})\n{output}\n'.format(**locals()))
    with s.shell.tempdir():
        with open('temp', 'w') as _file:
            _file.write(text)
        s.shell.run('less -R temp', interactive=True)


def main():
    s.shell.dispatch_commands(globals(), __name__)
