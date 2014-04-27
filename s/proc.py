from __future__ import absolute_import, print_function
import multiprocessing
import concurrent.futures
import s


_size = multiprocessing.cpu_count() + 2


_pool = s.thread._pool_factory()


submit = s.thread._submit_factory(concurrent.futures.ProcessPoolExecutor, globals())


new = s.thread._new_factory(multiprocessing.Process)
