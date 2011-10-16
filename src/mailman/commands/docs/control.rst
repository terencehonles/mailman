=============================
Starting and stopping Mailman
=============================

The Mailman daemon processes can be started and stopped from the command
line.


Set up
======

All we care about is the master process; normally it starts a bunch of
runners, but we don't care about any of them, so write a test configuration
file for the master that disables all the runners.

    >>> from mailman.commands.tests.test_control import make_config


Starting
========

    >>> from mailman.commands.cli_control import Start
    >>> start = Start()

    >>> class FakeArgs:
    ...     force = False
    ...     run_as_user = True
    ...     quiet = False
    ...     config = make_config()
    >>> args = FakeArgs()

Starting the daemons prints a useful message and starts the master watcher
process in the background.

    >>> start.process(args)
    Starting Mailman's master runner

    >>> from mailman.commands.tests.test_control import find_master

The process exists, and its pid is available in a run time file.

    >>> pid = find_master()
    >>> pid is not None
    True


Stopping
========

You can also stop the master watcher process from the command line, which
stops all the child processes too.
::

    >>> from mailman.commands.cli_control import Stop
    >>> stop = Stop()
    >>> stop.process(args)
    Shutting down Mailman's master runner

    >>> from datetime import datetime, timedelta
    >>> import os
    >>> import time
    >>> import errno
    >>> def bury_master():
    ...     until = timedelta(seconds=2) + datetime.now()
    ...     while datetime.now() < until:
    ...         time.sleep(0.1)
    ...         try:
    ...             os.kill(pid, 0)
    ...             os.waitpid(pid, os.WNOHANG)
    ...         except OSError as error:
    ...             if error.errno == errno.ESRCH:
    ...                 # The process has exited.
    ...                 print 'Master process went bye bye'
    ...                 return
    ...             else:
    ...                 raise
    ...     else:
    ...         raise AssertionError('Master process lingered')

    >>> bury_master()
    Master process went bye bye


XXX We need tests for restart (SIGUSR1) and reopen (SIGHUP).
