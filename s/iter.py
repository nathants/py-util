import itertools


def groupby(val, key):
    val = sorted(val, key=key)
    return [(k, list(v)) for k, v in itertools.groupby(val, key=key)]
