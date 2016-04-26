import itertools
import math

# TODO merge seq and iter?

def groupby(val, key):
    val = sorted(val, key=key)
    return [(k, list(v)) for k, v in itertools.groupby(val, key=key)]


def nwise(val, n):
    return zip(*(itertools.islice(val, i, None) for i, val in enumerate(itertools.tee(val, n))))


def chunk(val, chunk_size, drop_extra=False):
    res = ()
    for x in val:
        res += (x,)
        if len(res) == chunk_size:
            yield res
            res = ()
    if res and not drop_extra:
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
