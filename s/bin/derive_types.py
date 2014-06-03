from __future__ import absolute_import, print_function
import copy
import re
import s
import types
import argh
import logging


_state = {'doit': False}


def _cleanup(val):
    val = ''.join(re.split(r"<(?:type|class) '([^']+)'>", str(val)))
    val = re.split(r"(?:set|frozenset)\(\[([^\]]+)\]\)", str(val))
    val = ''.join([x if (i + 1) % 2 else '{%s}' % x for i, x in enumerate(val)])
    val = val.replace('NoneType', 'None')
    val = val.replace('frozenset', 'set')
    return val


def _logit(val, no_parse_types):
    def decorator(decoratee):
        def decorated(*a, **kw):
            try:
                try:
                    _a = copy.deepcopy(a)
                except:
                    _a = a

                try:
                    _kw = copy.deepcopy(kw)
                except:
                    _kw = kw

                res = decoratee(*a, **kw)

                try:
                    _res = copy.deepcopy(res)
                except:
                    _res = res

                if _state['doit']:
                    if no_parse_types:
                        val.add((tuple(str(x) for x in _a),
                                 (tuple((str(k), str(v)) for k, v in _kw.items())),
                                 str(_res)))

                    else:
                        val.add((tuple(_cleanup(s.types.parse(x)) for x in _a),
                                 tuple((_cleanup(k), _cleanup(s.types.parse(v))) for k, v in _kw.items()),
                                 _cleanup(s.types.parse(_res))))

                return res
            except:
                # logging.exception('huh?') # for debugging only, tests raise lots of exceptions in normal behavior
                raise
        return decorated
    return decorator

def _proceed(k, v, module_name):
    return (type(v) is types.FunctionType
            and getattr(v, '__module__', None) == module_name
            and not k.startswith('_'))



@argh.arg('where', nargs='?', default='.')
def _main(where, no_parse_types=False, regex='.*'):
    data = {}

    with s.shell.cd(where):
        skips = ['types.py', 'log.py']
        filepaths = [x for x in s.test.all_code_files() if not any(x.endswith(y) for y in skips)]
        testpaths = [x for x in s.test.all_fast_test_files() if not any(x.endswith(y) for y in skips)]
        for path in filepaths:
            module_name = s.shell.module_name(path)
            data[module_name] = _data = {}
            module = __import__(module_name, fromlist='*')
            for k, v in module.__dict__.items():
                if k not in ['__builtins__', '__builtin__']:
                    if _proceed(k, v, module_name):
                        x = set()
                        module.__dict__[k] = _logit(x, no_parse_types)(v)
                        _data[k] = x

    _state['doit'] = True
    for path in testpaths:
        s.test._test(path)
    _state['doit'] = False

    for path, results in data.items():

        text = ''

        for name, usages in sorted(results.items()):
            if not re.search(regex, path + name):
                continue

            text += '\n\n {}'.format(s.colors.blue(name))
            val = []
            for a, kw, res in usages:
                args = kwargs = ''
                if a:
                    args = ', '.join(a)
                if kw:
                    kwargs = ', '.join('{}={}'.format(k, v) for k, v in kw)
                    if a:
                        kwargs = ', ' + kwargs
                val.append('\n  ({}{}) -> {}'.format(args, kwargs, res))
            text += ''.join(sorted(val))

        if text:
            logging.info('\n' + s.colors.green(path) + text)



def main():
    s.log.setup(format='%(message)s')
    argh.dispatch_command(_main)
