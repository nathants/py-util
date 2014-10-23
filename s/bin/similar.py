from __future__ import print_function, absolute_import
import s
import os
import argh


_cmd = r"pylint {} --rcfile <(echo -e '[SIMILARITIES]\nmin-similarity-lines={}')"


def _get_output(cmd):
    return s.shell.run(cmd, warn=True)['output']


def _main(min_similar_lines=1):
    with s.shell.climb_git_root():
        dir_name = os.path.basename(os.getcwd())
        cmd = _cmd.format(dir_name, min_similar_lines)
        lines = _get_output(cmd).splitlines()
        while lines:
            first_line = lines.pop(0)
            if 'Similar' in first_line:
                text = ''
                for line in lines:
                    if line.startswith('R:') or line.startswith('Report'):
                        break
                    text += '\n' + line
                if 'import' not in text:
                    print(text)


def main():
    argh.dispatch_command(_main)
