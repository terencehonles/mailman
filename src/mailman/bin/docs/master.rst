======================
Mailman runner control
======================

Mailman has a number of *runner subprocesses* which perform long-running tasks
such as listening on an LMTP port, processing REST API requests, or processing
messages in a queue directory.  In normal operation, the ``bin/mailman``
command is used to start, stop and manage the runners.  This is just a wrapper
around the real master watcher, which handles runner starting, stopping,
exiting, and log file reopening.

    >>> from mailman.testing.helpers import TestableMaster

Start the master in a sub-thread.

    >>> master = TestableMaster()
    >>> master.start()

There should be a process id for every runner that claims to be startable.

    >>> from lazr.config import as_boolean
    >>> startable_runners = [conf for conf in config.runner_configs
    ...                      if as_boolean(conf.start)]
    >>> len(list(master.runner_pids)) == len(startable_runners)
    True

Now verify that all the runners are running.
::

    >>> import os

    # This should produce no output.
    >>> for pid in master.runner_pids:
    ...     os.kill(pid, 0)

Stop the master process, which should also kill (and not restart) the child
runner processes.

    >>> master.stop()

None of the children are running now.

    >>> import errno
    >>> for pid in master.runner_pids:
    ...     try:
    ...         os.kill(pid, 0)
    ...         print 'Process did not exit:', pid
    ...     except OSError as error:
    ...         if error.errno == errno.ESRCH:
    ...             # The child process exited.
    ...             pass
    ...         else:
    ...             raise
