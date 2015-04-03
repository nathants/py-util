import itertools
import six


def groupby(val, key, realize=True):
    val = sorted(val, key=key)
    if realize:
        return [(k, list(v)) for k, v in itertools.groupby(val, key=key)]
    else:
        return itertools.groupby(val, key=key)


def nwise(val, n):
    return six.moves.zip(*(itertools.islice(val, i, None) for i, val in enumerate(itertools.tee(val, n))))


def chunk(val, n, drop_extra=False):
    res = ()
    for x in val:
        res += (x,)
        if len(res) == n:
            yield res
            res = ()
    if res and not drop_extra:
        yield res
