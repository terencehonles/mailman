# Copyright (C) 2001-2009 by the Free Software Foundation, Inc.
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

"""Master sub-process watcher."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'main',
    ]


import os
import sys
import time
import errno
import signal
import socket
import logging

from datetime import datetime, timedelta
from lazr.config import as_boolean
from locknix import lockfile
from munepy import Enum

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
Master sub-process watcher.

Start and watch the configured queue runners and ensure that they stay alive
and kicking.  Each are fork and exec'd in turn, with the master waiting on
their process ids.  When it detects a child queue runner has exited, it may
restart it.

The queue runners respond to SIGINT, SIGTERM, SIGUSR1 and SIGHUP.  SIGINT,
SIGTERM and SIGUSR1 all cause the qrunners to exit cleanly.  The master will
restart qrunners that have exited due to a SIGUSR1 or some kind of other exit
condition (say because of an exception).  SIGHUP causes the master and the
qrunners to close their log files, and reopen then upon the next printed
message.

The master also responds to SIGINT, SIGTERM, SIGUSR1 and SIGHUP, which it
simply passes on to the qrunners.  Note that the master will close and reopen
its own log files on receipt of a SIGHUP.  The master also leaves its own
process id in the file `data/master-qrunner.pid` but you normally don't need
to use this pid directly.

Usage: %prog [options]""")

    def add_options(self):
        """See `Options`."""
        self.parser.add_option(
            '-n', '--no-restart',
            dest='restartable', default=True, action='store_false',
            help=_("""\
Don't restart the qrunners when they exit because of an error or a SIGUSR1.
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
Override the default set of queue runners that the master watch will invoke
instead of the default set.  Multiple -r options may be given.  The values for
-r are passed straight through to bin/qrunner."""))

    def sanity_check(self):
        """See `Options`."""
        if len(self.arguments) > 0:
            self.parser.error(_('Too many arguments'))



def get_lock_data():
    """Get information from the master lock file.

    :return: A 3-tuple of the hostname, integer process id, and file name of
        the lock file.
    """
    with open(config.LOCK_FILE) as fp:
        filename = os.path.split(fp.read().strip())[1]
    parts = filename.split('.')
    hostname = DOT.join(parts[1:-2])
    pid = int(parts[-2])
    return hostname, int(pid), filename


# pylint: disable-msg=W0232
class WatcherState(Enum):
    """Enum for the state of the master process watcher."""
    # Another master watcher is running.
    conflict = 1
    # No conflicting process exists.
    stale_lock = 2
    # Hostname from lock file doesn't match.
    host_mismatch = 3


def master_state():
    """Get the state of the master watcher.

    :return: WatcherState describing the state of the lock file.
    """
    # pylint: disable-msg=W0612
    hostname, pid, tempfile = get_lock_data()
    if hostname != socket.gethostname():
        return WatcherState.host_mismatch
    # Find out if the process exists by calling kill with a signal 0.
    try:
        os.kill(pid, 0)
        return WatcherState.conflict
    except OSError as error:
        if error.errno == errno.ESRCH:
            # No matching process id.
            return WatcherState.stale_lock
        # Some other error occurred.
        raise


def acquire_lock_1(force):
    """Try to acquire the master queue runner lock.

    :param force: Flag that controls whether to force acquisition of the lock.
    :return: The master queue runner lock.
    :raises: `TimeOutError` if the lock could not be acquired.
    """
    lock = lockfile.Lock(config.LOCK_FILE, LOCK_LIFETIME)
    try:
        lock.lock(timedelta(seconds=0.1))
        return lock
    except lockfile.TimeOutError:
        if not force:
            raise
        # Force removal of lock first.
        lock.disown()
        # pylint: disable-msg=W0612
        hostname, pid, tempfile = get_lock_data()
        os.unlink(config.LOCK_FILE)
        os.unlink(os.path.join(config.LOCK_DIR, tempfile))
        return acquire_lock_1(force=False)


def acquire_lock(force):
    """Acquire the master queue runner lock.

    :return: The master queue runner lock or None if the lock couldn't be
        acquired.  In that case, an error messages is also printed to standard
        error.
    """
    try:
        lock = acquire_lock_1(force)
        return lock
    except lockfile.TimeOutError:
        status = master_state()
        if status == WatcherState.conflict:
            # Hostname matches and process exists.
            message = _("""\
The master qrunner lock could not be acquired because it appears
as though another master qrunner is already running.
""")
        elif status == WatcherState.stale_lock:
            # Hostname matches but the process does not exist.
            message = _("""\
The master qrunner lock could not be acquired.  It appears as though there is
a stale master qrunner lock.  Try re-running mailmanctl with the -s flag.
""")
        else:
            # Hostname doesn't even match.
            assert status == WatcherState.host_mismatch, (
                'Invalid enum value: %s' % status)
            # pylint: disable-msg=W0612
            hostname, pid, tempfile = get_lock_data()
            message = _("""\
The master qrunner lock could not be acquired, because it appears as if some
process on some other host may have acquired it.  We can't test for stale
locks across host boundaries, so you'll have to clean this up manually.

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
            (queue-runner-name, slice-number, slice-count, restart-count)
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
            (queue-runner-name, slice-number, slice-count, restart-count)
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
            (queue-runner-name, slice-number, slice-count, restart-count)
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
        """Install various signals handlers for control from mailmanctl."""
        log = logging.getLogger('mailman.qrunner')
        # Set up our signal handlers.  Also set up a SIGALRM handler to
        # refresh the lock once per day.  The lock lifetime is 1 day + 6 hours
        # so this should be plenty.
        # pylint: disable-msg=W0613,C0111
        def sigalrm_handler(signum, frame):
            self._lock.refresh()
            signal.alarm(SECONDS_IN_A_DAY)
        signal.signal(signal.SIGALRM, sigalrm_handler)
        signal.alarm(SECONDS_IN_A_DAY)
        # SIGHUP tells the qrunners to close and reopen their log files.
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
        # levels.  It's also the signal 'mailmanctl stop' uses.
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
        """Start a queue runner.

        All arguments are passed to the qrunner process.

        :param spec: A queue runner spec, in a format acceptable to
            bin/qrunner's --runner argument, e.g. name:slice:count
        :type spec: string
        :return: The process id of the child queue runner.
        :rtype: int
        """
        pid = os.fork()
        if pid:
            # Parent.
            return pid
        # Child.
        #
        # Craft the command line arguments for the exec() call.
        rswitch = '--runner=' + spec
        # Wherever mailmanctl lives, so too must live the qrunner script.
        exe = os.path.join(config.BIN_DIR, 'qrunner')
        # config.PYTHON, which is the absolute path to the Python interpreter,
        # must be given as argv[0] due to Python's library search algorithm.
        args = [sys.executable, sys.executable, exe, rswitch, '-s']
        if self._config_file is not None:
            args.extend(['-C', self._config_file])
        log = logging.getLogger('mailman.qrunner')
        log.debug('starting: %s', args)
        os.execl(*args)
        # We should never get here.
        raise RuntimeError('os.execl() failed')

    def start_qrunners(self, qrunner_names=None):
        """Start all the configured qrunners.

        :param qrunners: If given, a sequence of queue runner names to start.
            If not given, this sequence is taken from the configuration file.
        :type qrunners: a sequence of strings
        """
        if not qrunner_names:
            qrunner_names = []
            for qrunner_config in config.qrunner_configs:
                # Strip off the 'qrunner.' prefix.
                assert qrunner_config.name.startswith('qrunner.'), (
                    'Unexpected qrunner configuration section name: %s',
                    qrunner_config.name)
                qrunner_names.append(qrunner_config.name[8:])
        # For each qrunner we want to start, find their config section, which
        # will tell us the name of the class to instantiate, along with the
        # number of hash space slices to manage.
        for name in qrunner_names:
            section_name = 'qrunner.' + name
            # Let AttributeError propagate.
            qrunner_config = getattr(config, section_name)
            if not as_boolean(qrunner_config.start):
                continue
            # Find out how many qrunners to instantiate.  This must be a power
            # of 2.
            count = int(qrunner_config.instances)
            assert (count & (count - 1)) == 0, (
                'Queue runner "%s", not a power of 2: %s', name, count)
            for slice_number in range(count):
                # qrunner name, slice #, # of slices, restart count
                info = (name, slice_number, count, 0)
                spec = '%s:%d:%d' % (name, slice_number, count)
                pid = self._start_runner(spec)
                log = logging.getLogger('mailman.qrunner')
                log.debug('[%d] %s', pid, spec)
                self._kids.add(pid, info)

    def _pause(self):
        """Sleep until a signal is received."""
        # Sleep until a signal is received.  This prevents the master from
        # existing immediately even if there are no qrunners (as happens in
        # the test suite).
        signal.pause()

    def loop(self):
        """Main loop.

        Wait until all the qrunners have exited, restarting them if necessary
        and configured to do so.
        """
        log = logging.getLogger('mailman.qrunner')
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
            qrname, slice_number, count, restarts = self._kids.pop(pid)
            config_name = 'qrunner.' + qrname
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
(pid: %d, why: %s, class: %s, slice: %d/%d) %s""",
                     pid, why, qrname, slice_number + 1, count,
                     ('[restarting]' if restart else ''))
            # See if we've reached the maximum number of allowable restarts
            if restarts > max_restarts:
                log.info("""\
qrunner %s reached maximum restart limit of %d, not restarting.""",
                         qrname, max_restarts)
            # Now perhaps restart the process unless it exited with a
            # SIGTERM or we aren't restarting.
            if restart:
                spec = '%s:%d:%d' % (qrname, slice_number, count)
                new_pid = self._start_runner(spec)
                new_info = (qrname, slice_number, count, restarts)
                self._kids.add(new_pid, new_info)

    def cleanup(self):
        """Ensure that all children have exited."""
        log = logging.getLogger('mailman.qrunner')
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
                # pylint: disable-msg=W0612
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

    # Acquire the master lock, exiting if we can't acquire it.  We'll let the
    # caller handle any clean up or lock breaking.  No with statement here
    # because Lock's constructor doesn't support a timeout.
    lock = acquire_lock(options.options.force)
    try:
        with open(config.PIDFILE, 'w') as fp:
            print >> fp, os.getpid()
        loop = Loop(lock, options.options.restartable, options.options.config)
        loop.install_signal_handlers()
        try:
            loop.start_qrunners(options.options.runners)
            loop.loop()
        finally:
            loop.cleanup()
            os.remove(config.PIDFILE)
    finally:
        lock.unlock()
