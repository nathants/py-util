from __future__ import print_function, absolute_import
import itertools


def walk(data, fn):
    data = fn(data)
    if isinstance(data, (list, tuple, set)):
        return type(data)(walk(x, fn) for x in data)
    elif isinstance(data, dict):
        return type(data)(walk(x, fn) for x in data.items())
    else:
        return data


def concat(*seqs):
    val = ()
    for seq in seqs:
        if isinstance(seq, (list, tuple, set)):
            val += tuple(seq)
        else:
            raise Exception('cannot concat: {} <{}>'.format(seq, type(seq).__name__))
    return val


def flatten(data):
    if isinstance(data, (list, tuple, set)):
        data = map(flatten, data)
        data = itertools.chain(*data)
        return tuple(data)
    elif isinstance(data, dict):
        data = itertools.chain(*data.items())
        data = map(flatten, data)
        data = itertools.chain(*data)
        return tuple(data)
    else:
        return (data,)
