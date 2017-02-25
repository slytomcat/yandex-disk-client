# Copyright 2009 Brian Quinlan. All Rights Reserved.
# Licensed to PSF under a Contributor Agreement.

"""Implements ThreadPoolExecutor."""

__author__ = 'Brian Quinlan (brian@sweetapp.com) modified by (Sly_tom_cat)slytomcat@mail.ru'

import atexit
from concurrent.futures import _base
from queue import Queue as _Queue
import threading
import weakref
from os import cpu_count

# Workers are created as daemon threads. This is done to allow the interpreter
# to exit when there are still idle threads in a ThreadPoolExecutor's thread
# pool (i.e. shutdown() was not called). However, allowing workers to die with
# the interpreter has two undesirable properties:
#   - The workers would still be running during interpretor shutdown,
#     meaning that they would fail in unpredictable ways.
#   - The workers could be killed while evaluating a work item, which could
#     be bad if the callable being evaluated has external side-effects e.g.
#     writing to a file.
#
# To work around this problem, an exit handler is installed which tells the
# workers to exit when their work queues are empty and then waits until the
# threads finish.

_threads_queues = weakref.WeakKeyDictionary()
_shutdown = False

class Queue(_Queue):
  ''' customized queue with added facility:
        unfinished() - returns total number of unfinished tasks = queue length + number of tasks
                       which were get from queue but still not reported as finished tasks.
  '''

  def unfinished(self):
    return self.unfinished_tasks

def _python_exit():
    global _shutdown
    _shutdown = True
    items = list(_threads_queues.items())
    if items:
        items[0][1].put(None)
    for t, q in items:
        t.join()

atexit.register(_python_exit)

class _WorkItem(object):
    def __init__(self, future, fn, args, kwargs):
        self.future = future
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self, task_done):
        if not self.future.set_running_or_notify_cancel():
            return

        try:
            result = self.fn(*self.args, **self.kwargs)
        except BaseException as e:
            task_done()
            self.future.set_exception(e)
        else:
            task_done()
            self.future.set_result(result)

def _worker(executor_reference, work_queue):
    try:
        while True:
            work_item = work_queue.get(block=True)
            if work_item is not None:
                work_item.run(work_queue.task_done)
                # Delete references to object. See issue16284
                del work_item
                continue
            executor = executor_reference()
            # Exit if:
            #   - The interpreter is shutting down OR
            #   - The executor that owns the worker has been collected OR
            #   - The executor that owns the worker has been shutdown.
            if _shutdown or executor is None or executor._shutdown:
                # Notice other workers
                work_queue.put(None)
                return
            del executor
    except BaseException:
        _base.LOGGER.critical('Exception in worker', exc_info=True)

class ThreadPoolExecutor(_base.Executor):
    def __init__(self, max_workers = None):
        """Initializes a new ThreadPoolExecutor instance.

        Args:
            max_workers: The maximum number of threads that can be used to
                execute the given calls.
        """
        if max_workers is None:
          self._max_workers = (cpu_count() or 1) * 5
        else:
          self._max_workers = max_workers
        self._work_queue = Queue()
        self._threads = set()
        self._shutdown = False
        self._shutdown_lock = threading.Lock()

    def unfinished(self):
      return self._work_queue.unfinished()

    def submit(self, fn, *args, **kwargs):
        with self._shutdown_lock:
            if self._shutdown:
                raise RuntimeError('cannot schedule new futures after shutdown')

            f = _base.Future()
            w = _WorkItem(f, fn, args, kwargs)

            self._work_queue.put(w)
            self._adjust_thread_count()

            return f
    submit.__doc__ = _base.Executor.submit.__doc__

    def _adjust_thread_count(self):
        # When the executor gets lost, the weakref callback will wake up
        # the worker threads.
        def weakref_cb(_, q=self._work_queue):
            q.put(None)
        # TODO(bquinlan): Should avoid creating new threads if there are more
        # idle threads than items in the work queue.
        # DONE(Sly_tom_cat): unfinished() is a total amount of currently executed
        # tasks and tasks in queue.
        working_threads = len(self._threads)
        if self._work_queue.unfinished() <= working_threads:
            # When number of threads is greater or equal to unfinished tasks then
            # there is no need to create a new thread.
            return
        if working_threads < self._max_workers:
            t = threading.Thread(target=_worker,
                                 args=(weakref.ref(self, weakref_cb),
                                       self._work_queue))
            t.daemon = True
            t.name = 'PoolExecutor#%d' % len(self._threads)
            t.start()
            self._threads.add(t)
            _threads_queues[t] = self._work_queue
            #print('\nPE: new thread created. Threads: %d' % len(self._threads))

    def shutdown(self, wait=True, fast=False):
        # fast - is a flag for fast shutdown: before putting in queue the stopping
        # task (None) the queue will be cleared. It means that all already executed
        # tasks will be finished, but (probably) all tasks in queue (PENDING) will be
        # canceled via _WorkItem.future.cancel()
        with self._shutdown_lock:
            self._shutdown = True
            if fast:
              while not self._work_queue.empty():
                w = self._work_queue.get()
                w.future.cancel()
                del w
            self._work_queue.put(None)
        if wait:
            for t in self._threads:
                t.join()
    shutdown.__doc__ = _base.Executor.shutdown.__doc__
