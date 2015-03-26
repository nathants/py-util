import s.shell
import s.web
import s.cached


def latest_version(name):
    return s.web.get_sync('http://pypi.python.org/pypi/%s/json' % name)['body']['info']['version']


def main():
    for line in s.shell.run('pip freeze').splitlines():
        if ' git+' not in line:
            name, version = line.split('==')
            latest = latest_version(name)
            if version != latest:
                print(name, version, '->', latest)
