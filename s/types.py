from __future__ import absolute_import, print_function
import s


def _list_remove_duplicates(obj):
    if not all(type(x) == type(obj[0]) for x in obj):
        return obj
    val = []
    val_set = set()
    for x in obj:
        if str(x) not in val_set:
            val_set.add(str(x))
            val.append(x)
    return val


def _list_remove_empties(obj):
    for x in obj:
        if isinstance(x, (list, tuple, dict)) and not x:
            if any(isinstance(y, type(x)) and y
                   for y in obj):
                obj.remove(x)
    return obj


def _list_fill_empties(obj): # TODO how the pha to write this saner?
    lists = all(isinstance(x, list) for x in obj)
    tuples = all(isinstance(x, list) for x in obj)
    if lists or tuples:
        if len({len(x) for x in obj}) == 1:
            for i, x in enumerate(obj):
                for j, y in enumerate(x):
                    if isinstance(y, (list, tuple)) and not y:
                        for _x in obj[i:]:
                            if isinstance(_x[j], type(y)) and _x[j]:
                                obj[i] = obj[i][:j] + [_x[j]] + obj[i][j + 1:]
    return obj


def _dict_number_dupe_keys(obj): # TODO implement more simply, groupby stringification is bad?
    val = []
    for k, g in s.iter.groupby(obj, lambda x: [str(x[0]), x[0]]):
        k = k[1]
        g = [x[1] for x in g]
        if len(g) == 1:
            val.append([k, g[0]])
        else:
            g = sorted(set(g), key=lambda x: str(x).lower())
            if len(g) == 1:
                val.append([k, g[0]])
            else:
                for i, x in enumerate(g):
                    val.append([(k, i), x])
    return val


def parse(obj):
    if isinstance(obj, (list, tuple)):
        cls = list if isinstance(obj, list) else tuple
        if not obj:
            return cls()
        obj = list(obj)
        obj = _list_fill_empties(obj)
        obj = [parse(x) for x in obj]
        obj = _list_remove_empties(obj)
        obj = _list_remove_duplicates(obj)
        return cls(obj)

    elif isinstance(obj, dict):
        obj = [(parse(k), parse(v)) for k, v in obj.items()]
        obj = _dict_number_dupe_keys(obj)
        return dict(obj)

    elif isinstance(obj, set):
        return {parse(x) for x in obj}

    else:
        return type(obj)
