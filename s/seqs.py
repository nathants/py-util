from __future__ import print_function, absolute_import
import itertools
import collections


def _type(x):
    if isinstance(x, collections.defaultdict):
        return dict
    else:
        return type(x)


def walk(fn, seq):
    seq = fn(seq)
    if isinstance(seq, (list, tuple, set)):
        return _type(seq)(walk(fn, x) for x in seq)
    elif isinstance(seq, dict):
        return _type(seq)(walk(fn, x) for x in seq.items())
    else:
        return seq


def concat(*seqs):
    val = ()
    for seq in seqs:
        if isinstance(seq, (list, tuple, set)):
            val += tuple(seq)
        else:
            raise Exception('cannot concat: {} <{}>'.format(seq, _type(seq).__name__))
    return val


def flatten(seq):
    if isinstance(seq, (list, tuple, set)):
        seq = map(flatten, seq)
        seq = itertools.chain(*seq)
        return tuple(seq)
    elif isinstance(seq, dict):
        seq = itertools.chain(*seq.items())
        seq = map(flatten, seq)
        seq = itertools.chain(*seq)
        return tuple(seq)
    else:
        return (seq,)


def split_with(pred, seq):
    a = list(itertools.takewhile(pred, seq))
    b = list(seq[len(a):])
    return [a, b]
