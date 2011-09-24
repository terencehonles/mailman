==============
Getting status
==============

The status of the Mailman master process can be queried from the command line.
It's clear at this point that nothing is running.
::

    >>> from mailman.commands.cli_status import Status
    >>> status = Status()

    >>> class FakeArgs:
    ...     pass

The status is printed to stdout and a status code is returned.

    >>> status.process(FakeArgs)
    GNU Mailman is not running
    0

We can simulate the master starting up by acquiring its lock.

    >>> from flufl.lock import Lock
    >>> lock = Lock(config.LOCK_FILE)
    >>> lock.lock()

Getting the status confirms that the master is running.

    >>> status.process(FakeArgs)
    GNU Mailman is running (master pid: ...

We shut down the master and confirm the status.

    >>> lock.unlock()
    >>> status.process(FakeArgs)
    GNU Mailman is not running
    0
