from __future__ import absolute_import, print_function
import re
import s
import types
import argh
import logging



def _cleanup(val):
    return ''.join(re.split(r"<(?:type|class) '([^']+)'>", str(val)))

def _logit(val):
    def decorator(decoratee):
        def decorated(*a, **kw):
            try:
                res = decoratee(*a, **kw)
                data = (tuple(_cleanup(s.types.parse(x)) for x in a),
                        tuple((_cleanup(k), _cleanup(s.types.parse(v))) for k, v in kw.items()),
                        _cleanup(s.types.parse(res)))
                val.add(data)
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
def _main(where):
    data = {}

    with s.shell.cd(where):
        filepaths = [x for x in s.test.all_code_files() if not x.endswith('types.py')]
        testpaths = [x for x in s.test.all_fast_test_files() if not x.endswith('types.py')]
        for path in filepaths:
            module_name = s.shell.module_name(path)
            data[module_name] = _data = {}
            module = __import__(module_name, fromlist='*')
            for k, v in module.__dict__.items():
                if k not in ['__builtins__', '__builtin__']:
                    if _proceed(k, v, module_name):
                        x = set()
                        module.__dict__[k] = _logit(x)(v)
                        _data[k] = v.__doc__, x

    for path in testpaths:
        s.test._test(path)

    for path, results in data.items():
        logging.info('')
        logging.info(path)
        for name, (signature, usages) in results.items():
            if not usages:
                continue
            logging.info('')
            logging.info('', signature or name)
            for a, kw, res in usages:
                args = kwargs = ''
                if a:
                    args = ', '.join(a)
                if kw:
                    kwargs = ', '.join('{}={}'.format(k, v) for k, v in kw)
                    if a:
                        kwargs = ', ' + kwargs
                logging.info(' ', '({}{}) -> {}'.format(args, kwargs, res))


def main():
    s.log.setup(format='%(message)s')
    argh.dispatch_command(_main)
