"""
create a ring like wrapper around tornado.
requests and responses are dicts.
handlers are coroutines which take req-dicts and return resp-dicts.
routes are declared like [('/path/(.*)/blah'), {'get': getfn, 'put': putfn}),
                          ('/', {'get': homefn})]
"""
