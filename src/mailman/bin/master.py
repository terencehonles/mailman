# Copyright (C) 2001-2012 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Master subprocess watcher."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Loop',
    'main',
    ]


import os
import sys
import errno
import signal
import socket
import logging

from datetime import timedelta
from flufl.enum import Enum
from flufl.lock import Lock, NotLockedError, TimeOutError
from lazr.config import as_boolean

from mailman.config import config
from mailman.core.i18n import _
from mailman.core.logging import reopen
from mailman.options import Options


DOT = '.'
LOCK_LIFETIME = timedelta(days=1, hours=6)
SECONDS_IN_A_DAY = 86400
SUBPROC_START_WAIT = timedelta(seconds=20)



class ScriptOptions(Options):
    """Options for the master watcher."""

    usage = _("""\
%prog [options]

Master subprocess watcher.

Start and watch the configured runners and ensure that they stay alive and
kicking.  Each runner is forked and exec'd in turn, with the master waiting on
their process ids.  When it detects a child runner has exited, it may restart
it.

The runners respond to SIGINT, SIGTERM, SIGUSR1 and SIGHUP.  SIGINT, SIGTERM
and SIGUSR1 all cause a runner to exit cleanly.  The master will restart
runners that have exited due to a SIGUSR1 or some kind of other exit condition
(say because of an uncaught exception).  SIGHUP causes the master and the
runners to close their log files, and reopen then upon the next printed
message.

The master also responds to SIGINT, SIGTERM, SIGUSR1 and SIGHUP, which it
simply passes on to the runners.  Note that the master will close and reopen
its own log files on receipt of a SIGHUP.  The master also leaves its own
process id in the file `data/master.pid` but you normally don't need to use
this pid directly.""")

    def add_options(self):
        """See `Options`."""
        self.parser.add_option(
            '-n', '--no-restart',
            dest='restartable', default=True, action='store_false',
            help=_("""\
Don't restart the runners when they exit because of an error or a SIGUSR1.
Use this only for debugging."""))
        self.parser.add_option(
            '-f', '--force',
            default=False, action='store_true',
            help=_("""\
If the master watcher finds an existing master lock, it will normally exit
with an error message.  With this option,the master will perform an extra
level of checking.  If a process matching the host/pid described in the lock
file is running, the master will still exit, requiring you to manually clean
up the lock.  But if no matching process is found, the master will remove the
apparently stale lock and make another attempt to claim the master lock."""))
        self.parser.add_option(
            '-r', '--runner',
            dest='runners', action='append', default=[],
            help=_("""\
Override the default set of runners that the master will invoke, which is
typically defined in the configuration file.  Multiple -r options may be
given.  The values for -r are passed straight through to bin/runner."""))

    def sanity_check(self):
        """See `Options`."""
        if len(self.arguments) > 0:
            self.parser.error(_('Too many arguments'))



class WatcherState(Enum):
    """Enum for the state of the master process watcher."""
    # No lock has been acquired by any process.
    none = 0
    # Another master watcher is running.
    conflict = 1
    # No conflicting process exists.
    stale_lock = 2
    # Hostname from lock file doesn't match.
    host_mismatch = 3


def master_state(lock_file=None):
    """Get the state of the master watcher.

    :param lock_file: Path to the lock file, otherwise `config.LOCK_FILE`.
    :type lock_file: str
    :return: 2-tuple of the WatcherState describing the state of the lock
        file, and the lock object.
    """
    if lock_file is None:
        lock_file = config.LOCK_FILE
    # We'll never acquire the lock, so the lifetime doesn't matter.
    lock = Lock(lock_file)
    try:
        hostname, pid, tempfile = lock.details
    except NotLockedError:
        return WatcherState.none, lock
    if hostname != socket.getfqdn():
        return WatcherState.host_mismatch, lock
    # Find out if the process exists by calling kill with a signal 0.
    try:
        os.kill(pid, 0)
        return WatcherState.conflict, lock
    except OSError as error:
        if error.errno == errno.ESRCH:
            # No matching process id.
            return WatcherState.stale_lock, lock
        # Some other error occurred.
        raise


def acquire_lock_1(force, lock_file=None):
    """Try to acquire the master lock.

    :param force: Flag that controls whether to force acquisition of the lock.
    :type force: bool
    :param lock_file: Path to the lock file, otherwise `config.LOCK_FILE`.
    :type lock_file: str
    :return: The master lock.
    :raises: `TimeOutError` if the lock could not be acquired.
    """
    if lock_file is None:
        lock_file = config.LOCK_FILE
    lock = Lock(lock_file, LOCK_LIFETIME)
    try:
        lock.lock(timedelta(seconds=0.1))
        return lock
    except TimeOutError:
        if not force:
            raise
        # Force removal of lock first.
        lock.disown()
        hostname, pid, tempfile = lock.details
        os.unlink(lock_file)
        return acquire_lock_1(force=False)


def acquire_lock(force):
    """Acquire the master lock.

    :param force: Flag that controls whether to force acquisition of the lock.
    :type force: bool
    :return: The master runner lock or None if the lock couldn't be acquired.
        In that case, an error messages is also printed to standard error.
    """
    try:
        lock = acquire_lock_1(force)
        return lock
    except TimeOutError:
        status, lock = master_state()
        if status is WatcherState.conflict:
            # Hostname matches and process exists.
            message = _("""\
The master lock could not be acquired because it appears as though another
master is already running.""")
        elif status is WatcherState.stale_lock:
            # Hostname matches but the process does not exist.
            program = sys.argv[0]
            message = _("""\
The master lock could not be acquired.  It appears as though there is a stale
master lock.  Try re-running $program with the --force flag.""")
        elif status is WatcherState.host_mismatch:
            # Hostname doesn't even match.
            hostname, pid, tempfile = lock.details
            message = _("""\
The master lock could not be acquired, because it appears as if some process
on some other host may have acquired it.  We can't test for stale locks across
host boundaries, so you'll have to clean this up manually.

Lock file: $config.LOCK_FILE
Lock host: $hostname

Exiting.""")
        else:
            assert status is WatcherState.none, (
                'Invalid enum value: ${0}'.format(status))
            hostname, pid, tempfile = lock.details
            message = _("""\
For unknown reasons, the master lock could not be acquired.


Lock file: $config.LOCK_FILE
Lock host: $hostname

Exiting.""")
        config.options.parser.error(message)



class PIDWatcher:
    """A class which safely manages child process ids."""

    def __init__(self):
        self._pids = {}

    def __iter__(self):
        # Safely iterate over all the keys in the dictionary.  Because
        # asynchronous signals are involved, the dictionary's size could
        # change during iteration.  Iterate over a copy of the keys to avoid
        # that.
        for pid in self._pids.keys():
            yield pid

    def add(self, pid, info):
        """Add process information.

        :param pid: The process id.  The watcher must not already be tracking
            this process id.
        :type pid: int
        :param info: The process information.
        :type info: 4-tuple consisting of
            (runner-name, slice-number, slice-count, restart-count)
        """
        old_info = self._pids.get(pid)
        assert old_info is None, (
            'Duplicate process id {0} with existing info: {1}'.format(
                pid, old_info))
        self._pids[pid] = info

    def pop(self, pid):
        """Remove and return existing process information.

        :param pid: The process id.  The watcher must already be tracking this
            process id.
        :type pid: int
        :return: The process information.
        :rtype: 4-tuple consisting of
            (runner-name, slice-number, slice-count, restart-count)
        :raise KeyError: if the process id is not being tracked.
        """
        return self._pids.pop(pid)

    def drop(self, pid):
        """Remove and return existing process information.

        This is like `pop()` except that no `KeyError` is raised if the
        process id is not being tracked.

        :param pid: The process id.
        :type pid: int
        :return: The process information, or None if the process id is not
            being tracked.
        :rtype: 4-tuple consisting of
            (runner-name, slice-number, slice-count, restart-count)
        """
        return self._pids.pop(pid, None)



class Loop:
    """Main control loop class."""

    def __init__(self, lock=None, restartable=None, config_file=None):
        self._lock = lock
        self._restartable = restartable
        self._config_file = config_file
        self._kids = PIDWatcher()

    def install_signal_handlers(self):
        """Install various signals handlers for control from the master."""
        log = logging.getLogger('mailman.runner')
        # Set up our signal handlers.  Also set up a SIGALRM handler to
        # refresh the lock once per day.  The lock lifetime is 1 day + 6 hours
        # so this should be plenty.
        def sigalrm_handler(signum, frame):
            self._lock.refresh()
            signal.alarm(SECONDS_IN_A_DAY)
        signal.signal(signal.SIGALRM, sigalrm_handler)
        signal.alarm(SECONDS_IN_A_DAY)
        # SIGHUP tells the runners to close and reopen their log files.
        def sighup_handler(signum, frame):
            reopen()
            for pid in self._kids:
                os.kill(pid, signal.SIGHUP)
            log.info('Master watcher caught SIGHUP.  Re-opening log files.')
        signal.signal(signal.SIGHUP, sighup_handler)
        # SIGUSR1 is used by 'mailman restart'.
        def sigusr1_handler(signum, frame):
            for pid in self._kids:
                os.kill(pid, signal.SIGUSR1)
            log.info('Master watcher caught SIGUSR1.  Exiting.')
        signal.signal(signal.SIGUSR1, sigusr1_handler)
        # SIGTERM is what init will kill this process with when changing run
        # levels.  It's also the signal 'bin/mailman stop' uses.
        def sigterm_handler(signum, frame):
            for pid in self._kids:
                os.kill(pid, signal.SIGTERM)
            log.info('Master watcher caught SIGTERM.  Exiting.')
        signal.signal(signal.SIGTERM, sigterm_handler)
        # SIGINT is what control-C gives.
        def sigint_handler(signum, frame):
            for pid in self._kids:
                os.kill(pid, signal.SIGINT)
            log.info('Master watcher caught SIGINT.  Restarting.')
        signal.signal(signal.SIGINT, sigint_handler)

    def _start_runner(self, spec):
        """Start a runner.

        All arguments are passed to the process.

        :param spec: A runner spec, in a format acceptable to
            bin/runner's --runner argument, e.g. name:slice:count
        :type spec: string
        :return: The process id of the child runner.
        :rtype: int
        """
        pid = os.fork()
        if pid:
            # Parent.
            return pid
        # Child.
        #
        # Set the environment variable which tells the runner that it's
        # running under bin/master control.  This subtly changes the error
        # behavior of bin/runner.
        os.environ['MAILMAN_UNDER_MASTER_CONTROL'] = '1'
        # Craft the command line arguments for the exec() call.
        rswitch = '--runner=' + spec
        # Wherever master lives, so too must live the runner script.
        exe = os.path.join(config.BIN_DIR, 'runner')
        # config.PYTHON, which is the absolute path to the Python interpreter,
        # must be given as argv[0] due to Python's library search algorithm.
        args = [sys.executable, sys.executable, exe, rswitch]
        if self._config_file is not None:
            args.extend(['-C', self._config_file])
        log = logging.getLogger('mailman.runner')
        log.debug('starting: %s', args)
        os.execl(*args)
        # We should never get here.
        raise RuntimeError('os.execl() failed')

    def start_runners(self, runner_names=None):
        """Start all the configured runners.

        :param runners: If given, a sequence of runner names to start.  If not
            given, this sequence is taken from the configuration file.
        :type runners: a sequence of strings
        """
        if not runner_names:
            runner_names = []
            for runner_config in config.runner_configs:
                # Strip off the 'runner.' prefix.
                assert runner_config.name.startswith('runner.'), (
                    'Unexpected runner configuration section name: {0}'.format(
                    runner_config.name))
                runner_names.append(runner_config.name[7:])
        # For each runner we want to start, find their config section, which
        # will tell us the name of the class to instantiate, along with the
        # number of hash space slices to manage.
        for name in runner_names:
            section_name = 'runner.' + name
            # Let AttributeError propagate.
            runner_config = getattr(config, section_name)
            if not as_boolean(runner_config.start):
                continue
            # Find out how many runners to instantiate.  This must be a power
            # of 2.
            count = int(runner_config.instances)
            assert (count & (count - 1)) == 0, (
                'Runner "{0}", not a power of 2: {1}'.format(name, count))
            for slice_number in range(count):
                # runner name, slice #, # of slices, restart count
                info = (name, slice_number, count, 0)
                spec = '{0}:{1:d}:{2:d}'.format(name, slice_number, count)
                pid = self._start_runner(spec)
                log = logging.getLogger('mailman.runner')
                log.debug('[{0:d}] {1}'.format(pid, spec))
                self._kids.add(pid, info)

    def _pause(self):
        """Sleep until a signal is received."""
        # Sleep until a signal is received.  This prevents the master from
        # exiting immediately even if there are no runners (as happens in the
        # test suite).
        signal.pause()

    def loop(self):
        """Main loop.

        Wait until all the runner subprocesses have exited, restarting them if
        necessary and configured to do so.
        """
        log = logging.getLogger('mailman.runner')
        self._pause()
        while True:
            try:
                pid, status = os.wait()
            except OSError as error:
                # No children?  We're done.
                if error.errno == errno.ECHILD:
                    break
                # If the system call got interrupted, just restart it.
                elif error.errno == errno.EINTR:
                    continue
                else:
                    raise
            # Find out why the subprocess exited by getting the signal
            # received or exit status.
            if os.WIFSIGNALED(status):
                why = os.WTERMSIG(status)
            elif os.WIFEXITED(status):
                why = os.WEXITSTATUS(status)
            else:
                why = None
            # We'll restart the subprocess if it exited with a SIGUSR1 or
            # because of a failure (i.e. no exit signal), and the no-restart
            # command line switch was not given.  This lets us better handle
            # runaway restarts (e.g.  if the subprocess had a syntax error!)
            rname, slice_number, count, restarts = self._kids.pop(pid)
            config_name = 'runner.' + rname
            restart = False
            if why == signal.SIGUSR1 and self._restartable:
                restart = True
            # Have we hit the maximum number of restarts?
            restarts += 1
            max_restarts = int(getattr(config, config_name).max_restarts)
            if restarts > max_restarts:
                restart = False
            # Are we permanently non-restartable?
            log.debug("""\
Master detected subprocess exit
(pid: {0:d}, why: {1}, class: {2}, slice: {3:d}/{4:d}) {5}""".format(
                     pid, why, rname, slice_number + 1, count,
                     ('[restarting]' if restart else '')))
            # See if we've reached the maximum number of allowable restarts.
            if restarts > max_restarts:
                log.info("""\
Runner {0} reached maximum restart limit of {1:d}, not restarting.""",
                         rname, max_restarts)
            # Now perhaps restart the process unless it exited with a
            # SIGTERM or we aren't restarting.
            if restart:
                spec = '{0}:{1:d}:{2:d}'.format(rname, slice_number, count)
                new_pid = self._start_runner(spec)
                new_info = (rname, slice_number, count, restarts)
                self._kids.add(new_pid, new_info)

    def cleanup(self):
        """Ensure that all children have exited."""
        log = logging.getLogger('mailman.runner')
        # Send SIGTERMs to all the child processes and wait for them all to
        # exit.
        for pid in self._kids:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as error:
                if error.errno == errno.ESRCH:
                    # The child has already exited.
                    log.info('ESRCH on pid: %d', pid)
        # Wait for all the children to go away.
        while self._kids:
            try:
                pid, status = os.wait()
                self._kids.drop(pid)
            except OSError as error:
                if error.errno == errno.ECHILD:
                    break
                elif error.errno == errno.EINTR:
                    continue
                raise



def main():
    """Main process."""

    options = ScriptOptions()
    options.initialize()
    # Acquire the master lock, exiting if we can't.  We'll let the caller
    # handle any clean up or lock breaking.  No `with` statement here because
    # Lock's constructor doesn't support a timeout.
    lock = acquire_lock(options.options.force)
    try:
        with open(config.PID_FILE, 'w') as fp:
            print >> fp, os.getpid()
        loop = Loop(lock, options.options.restartable, options.options.config)
        loop.install_signal_handlers()
        try:
            loop.start_runners(options.options.runners)
            loop.loop()
        finally:
            loop.cleanup()
            os.remove(config.PID_FILE)
    finally:
        lock.unlock()
