from __future__ import print_function, absolute_import
import s.exceptions


def is_future(obj):
    with s.exceptions.ignore(AttributeError):
        object.__getattribute__(obj, 'add_done_callback')
        return True
