import itertools
import math
import re

# TODO merge seq and iter?


def percentile(xs, n):
    """percentile where xs like [1, 2, 3] and n like 99"""
    size = len(xs)
    index = math.ceil(n / 100. * size) - 1
    index = min(index, size - 1)
    index = max(index, 0)
    return sorted(xs)[int(index)]


def groupby(val, key):
    val = sorted(val, key=key)
    return [(k, list(v)) for k, v in itertools.groupby(val, key=key)]


def nwise(val, n):
    return zip(*(itertools.islice(val, i, None) for i, val in enumerate(itertools.tee(val, n))))


class _empty():
    pass


def partition_by(val, pred):
    """note: you must fully consume each partition before advancing to the next"""
    val = iter(val)
    def f():
        nonlocal val
        last = _empty
        while True:
            now = next(val)
            if last is _empty or pred(last) == pred(now):
                yield now
                last = now
            else:
                val = itertools.chain([now], val)
                break
    while True:
        part = f()
        head = next(part)
        yield itertools.chain([head], part)


def ichunk(val, chunk_size, drop_extra=False):
    """note: you must fully consume each chunk before advancing to the next"""
    while True:
        xs = itertools.islice(val, chunk_size)
        head = next(xs)
        yield itertools.chain([head], xs)


def chunk(val, chunk_size):
    res = []
    for x in val:
        res.append(x)
        if len(res) == chunk_size:
            yield res
            res = []
    if res:
        yield res


def chunks(val, num_chunks):
    size = len(val)
    step = math.ceil(size / num_chunks)
    return (t
            for i in range(num_chunks)
            for t in [tuple(val[step * i:step * (i + 1)])]
            if t)


def histogram(xs, size, exp=False):
    def check(x):
        assert x > 0, 'histogram only supports values > 0, not: %s' % x
        return x
    xs = map(check, xs)
    xs = groupby(xs, lambda x: x // (size + 1))
    xs = [('%s-%s' % (k * size + 1,
                      (k + 1) * size),
           len(v))
          for k, v in xs]
    if exp:
        new = []
        i = 1
        while True:
            vals = [xs.pop(0) for _ in range(i) if xs]
            name = '%s-%s' % (vals[0][0].split('-')[0], vals[-1][0].split('-')[-1])
            val = sum(x[1] for x in vals)
            new.append((name, val))
            i *= 2
            if not xs:
                xs = new
                break
    return xs


def alphanumeric_key(x):
    """use this as a key fn for sorted. based on http://stackoverflow.com/a/2669120"""
    ys = re.split('([0-9]+)', x)
    return [int(y)
            if y.isdigit()
            else y
            for y in ys]
