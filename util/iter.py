import itertools
import collections
import math
import re

# ? is this a subset of: https://github.com/erikrose/more-itertools/tree/master/more_itertools

def percentile(xs, n):
    """percentile where xs like [1, 2, 3] and n like 99"""
    size = len(xs)
    index = math.ceil(n / 100. * size) - 1
    index = min(index, size - 1)
    index = max(index, 0)
    return sorted(xs)[int(index)]

def groupby(val, key):
    val = sorted(val, key=key)
    return [(bucket, list(v)) for bucket, v in itertools.groupby(val, key=key)]

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
            try:
                now = next(val)
            except StopIteration:
                break
            else:
                if last is _empty or pred(last) == pred(now):
                    yield now
                    last = now
                else:
                    val = itertools.chain([now], val)
                    break
    while True:
        part = f()
        try:
            head = next(part)
        except StopIteration:
            break
        else:
            yield itertools.chain([head], part)

def ichunk(val, chunk_size):
    """note: you must fully consume each chunk before advancing to the next"""
    val = iter(val)
    while True:
        xs = itertools.islice(val, chunk_size)
        try:
            head = next(xs)
        except StopIteration:
            break
        else:
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

def histogram(xs, size, exponential=False, accumulate=False, key=lambda x: x):
    counts = collections.Counter()
    accum = collections.defaultdict(list)
    for x in xs:
        assert key(x) >= 0, 'histogram only supports values >= 0, not: %s' % x
        bucket = key(x) // size
        counts[bucket] += 1
        accum[bucket] += [x]
    results = [('%s-%s' % (bucket * size, (bucket + 1) * size - 1),
                (accum if accumulate else counts)[bucket])
               for bucket in sorted(counts)]
    if exponential:
        new = []
        i = 1
        while True:
            vals = [results.pop(0) for _ in range(i) if results]
            name = '%s-%s' % (vals[0][0].split('-')[0], vals[-1][0].split('-')[-1])
            val = sum([x[1] for x in vals], [] if accumulate else 0)
            new.append((name, val))
            i *= 2
            if not results:
                results = new
                break
    return results

def alphanumeric_key(x):
    """use this as a key fn for sorted. based on http://stackoverflow.com/a/2669120"""
    ys = re.split('([0-9]+)', x)
    return [int(y)
            if y.isdigit()
            else y
            for y in ys]

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
