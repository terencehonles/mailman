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

    >>> import shutil
    >>> from os.path import dirname, join
    >>> config_file = join(dirname(config.filename), 'no-runners.cfg')
    >>> shutil.copyfile(config.filename, config_file)
    >>> with open(config_file, 'a') as fp:
    ...     print >> fp, """\
    ... [runner.archive]
    ... start: no
    ... [runner.bounces]
    ... start: no
    ... [runner.command]
    ... start: no
    ... [runner.in]
    ... start: no
    ... [runner.lmtp]
    ... start: no
    ... [runner.news]
    ... start: no
    ... [runner.out]
    ... start: no
    ... [runner.pipeline]
    ... start: no
    ... [runner.rest]
    ... start: no
    ... [runner.retry]
    ... start: no
    ... [runner.virgin]
    ... start: no
    ... [runner.digest]
    ... start: no
    ... """


Starting
========

    >>> from mailman.commands.cli_control import Start
    >>> start = Start()

    >>> class FakeArgs:
    ...     force = False
    ...     run_as_user = True
    ...     quiet = False
    ...     config = config_file
    >>> args = FakeArgs()

Starting the daemons prints a useful message and starts the master watcher
process in the background.

    >>> start.process(args)
    Starting Mailman's master runner

    >>> import errno, os, time
    >>> from datetime import timedelta, datetime
    >>> def find_master():
    ...     until = timedelta(seconds=10) + datetime.now()
    ...     while datetime.now() < until:
    ...         time.sleep(0.1)
    ...         try:
    ...             with open(config.PID_FILE) as fp:
    ...                 pid = int(fp.read().strip())
    ...             os.kill(pid, 0)
    ...         except IOError as error:
    ...             if error.errno != errno.ENOENT:
    ...                 raise
    ...         except ValueError:
    ...             pass
    ...         except OSError as error:
    ...             if error.errno != errno.ESRCH:
    ...                 raise
    ...         else:
    ...             print 'Master process found'
    ...             return pid
    ...     else:
    ...         raise AssertionError('No master process')

The process exists, and its pid is available in a run time file.

    >>> pid = find_master()
    Master process found


Stopping
========

You can also stop the master watcher process from the command line, which
stops all the child processes too.

    >>> from mailman.commands.cli_control import Stop
    >>> stop = Stop()
    >>> stop.process(args)
    Shutting down Mailman's master runner

    >>> def bury_master():
    ...     until = timedelta(seconds=10) + datetime.now()
    ...     while datetime.now() < until:
    ...         time.sleep(0.1)
    ...         try:
    ...             import sys
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
