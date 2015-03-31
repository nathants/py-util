json_types = (
    list,
    str,
    dict,
    int,
    float,
    tuple,
    bool,
    type(None),
)


try:
    json_types += (unicode,) # noqa
except:
    pass


string_types = (str,)


try:
    string_types += (unicode,) # noqa
except:
    pass
