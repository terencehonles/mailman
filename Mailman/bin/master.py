# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

from __future__ import with_statement

import os
import grp
import pwd
import sys
import errno
import signal
import socket
import logging
import optparse

from datetime import timedelta
from locknix import lockfile
from munepy import Enum

from Mailman import Defaults
from Mailman import Version
from Mailman import loginit
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.initialize import initialize


COMMASPACE = ', '
DOT = '.'
# Calculate this here and now, because we're going to do a chdir later on, and
# if the path is relative, the qrunner script won't be found.
BIN_DIR = os.path.abspath(os.path.dirname(sys.argv[0]))

# Since we wake up once per day and refresh the lock, the LOCK_LIFETIME
# needn't be (much) longer than SNOOZE.  We pad it 6 hours just to be safe.
LOCK_LIFETIME = Defaults.days(1) + Defaults.hours(6)
SNOOZE = Defaults.days(1)

log = None
parser = None



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
Master queue runner watcher.

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

Usage: %prog [options]"""))
    parser.add_option('-n', '--no-restart',
                      dest='restartable', default=True, action='store_false',
                      help=_("""\
Don't restart the qrunners when they exit because of an error or a SIGUSR1.
Use this only for debugging."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    options, arguments = parser.parse_args()
    if len(arguments) > 0:
        parser.error(_('Too many arguments'))
    parser.options = options
    parser.arguments = arguments
    return parser



def get_lock_data():
    """Get information from the master lock file.

    :return: A 3-tuple of the hostname, integer process id, and file name of
        the lock file.
    """
    with open(config.LOCK_FILE) as fp:
        filename = os.path.split(fp.read().strip())[1]
    parts = filename.split('.')
    hostname = DOT.join(parts[1:-1])
    pid = int(parts[-1])
    return hostname, int(pid), filename


class WatcherState(Enum):
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

    # 1 if proc exists on host (but is it qrunner? ;)
    # 0 if host matches but no proc
    # hostname if hostname doesn't match
    hostname, pid, tempfile = get_lock_data()
    if hostname <> socket.gethostname():
        return WatcherState.host_mismatch
    # Find out if the process exists by calling kill with a signal 0.
    try:
        os.kill(pid, 0)
        return WatcherState.conflict
    except OSError, e:
        if e.errno == errno.ESRCH:
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
        hostname, pid, tempfile = get_lock_data()
        os.unlink(config.LOCK_FILE)
        os.unlink(os.path.join(config.LOCK_DIR, tempfile))
        return acquire_lock_1(force=False)


def acquire_lock(force):
    """Acquire the master queue runner lock.

    :param force: Flag that controls whether to force acquisition of the lock.
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
            print >> sys.stderr, _("""\
The master qrunner lock could not be acquired because it appears as if another
master qrunner is already running.
""")
        elif status == WatcherState.stale_lock:
            # Hostname matches but the process does not exist.
            print >> sys.stderr, _("""\
The master qrunner lock could not be acquired.  It appears as though there is
a stale master qrunner lock.  Try re-running mailmanctl with the -s flag.
""")
        else:
            assert status == WatcherState.host_mismatch, (
                'Invalid enum value: %s' % status)
            # Hostname doesn't even match.
            print >> sys.stderr, _("""\
The master qrunner lock could not be acquired, because it appears as if some
process on some other host may have acquired it.  We can't test for stale
locks across host boundaries, so you'll have to do this manually.  Or, if you
know the lock is stale, re-run mailmanctl with the -s flag.

Lock file: $config.LOCK_FILE
Lock host: $status

Exiting.""")
        return None



def start_runner(qrname, slice, count):
    """Start a queue runner.

    All arguments are passed to the qrunner process.

    :param qrname: The name of the queue runner.
    :param slice: The slice number.
    :param count: The total number of slices.
    :return: The process id of the child queue runner.
    """
    pid = os.fork()
    if pid:
        # Parent.
        return pid
    # Child.
    #
    # Craft the command line arguments for the exec() call.
    rswitch = '--runner=%s:%d:%d' % (qrname, slice, count)
    # Wherever mailmanctl lives, so too must live the qrunner script.
    exe = os.path.join(BIN_DIR, 'qrunner')
    # config.PYTHON, which is the absolute path to the Python interpreter,
    # must be given as argv[0] due to Python's library search algorithm.
    args = [sys.executable, sys.executable, exe, rswitch, '-s']
    if parser.options.config:
        args.extend(['-C', parser.options.config])
    log.debug('starting: %s', args)
    os.execl(*args)
    # We should never get here.
    raise RuntimeError('os.execl() failed')



def control_loop(lock):
    """The main control loop.

    This starts up the queue runners, watching for their exit and restarting
    them if need be.
    """
    restartable = parser.options.restartable
    # Start all the qrunners.  Keep a dictionary mapping process ids to
    # information about the child processes.
    kids = {}
    # Set up our signal handlers.  Also set up a SIGALRM handler to refresh
    # the lock once per day.  The lock lifetime is 1 day + 6 hours so this
    # should be plenty.
    def sigalrm_handler(signum, frame):
        lock.refresh()
        signal.alarm(int(Defaults.days(1)))
    signal.signal(signal.SIGALRM, sigalrm_handler)
    signal.alarm(int(Defaults.days(1)))
    # SIGHUP tells the qrunners to close and reopen their log files.
    def sighup_handler(signum, frame):
        loginit.reopen()
        for pid in kids:
            os.kill(pid, signal.SIGHUP)
        log.info('Master watcher caught SIGHUP.  Re-opening log files.')
    signal.signal(signal.SIGHUP, sighup_handler)
    # SIGUSR1 is used by 'mailman restart'.
    def sigusr1_handler(signum, frame):
        for pid in kids:
            os.kill(pid, signal.SIGUSR1)
        log.info('Master watcher caught SIGUSR1.  Exiting.')
    signal.signal(signal.SIGUSR1, sigusr1_handler)
    # SIGTERM is what init will kill this process with when changing run
    # levels.  It's also the signal 'mailmanctl stop' uses.
    def sigterm_handler(signum, frame):
        for pid in kids:
            os.kill(pid, signal.SIGTERM)
        log.info('Master watcher caught SIGTERM.  Exiting.')
    signal.signal(signal.SIGTERM, sigterm_handler)
    # SIGINT is what control-C gives.
    def sigint_handler(signum, frame):
        for pid in kids:
            os.kill(pid, signal.SIGINT)
        log.info('Master watcher caught SIGINT.  Restarting.')
    signal.signal(signal.SIGINT, sigint_handler)
    # Start all the child qrunners.
    for qrname, count in config.qrunners.items():
        for slice_number in range(count):
            # queue runner name, slice number, number of slices, restart count
            info = (qrname, slice_number, count, 0)
            pid = start_runner(qrname, slice_number, count)
            kids[pid] = info
    # Enter the main wait loop.
    try:
        while True:
            try:
                pid, status = os.wait()
            except OSError, error:
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
            qrname, slice, count, restarts = kids.pop(pid)
            restart = False
            if why == signal.SIGUSR1 and restartable:
                restart = True
            # Have we hit the maximum number of restarts?
            restarts += 1
            if restarts > config.MAX_RESTARTS:
                restart = False
            # Are we permanently non-restartable?
            log.debug("""\
Master detected subprocess exit
(pid: %d, why: %s, class: %s, slice: %d/%d) %s""",
                     pid, why, qrname, slice+1, count,
                     ('[restarting]' if restart else ''))
            # See if we've reached the maximum number of allowable restarts
            if restarts > config.MAX_RESTARTS:
                log.info("""\
qrunner %s reached maximum restart limit of %d, not restarting.""",
                         qrname, config.MAX_RESTARTS)
            # Now perhaps restart the process unless it exited with a
            # SIGTERM or we aren't restarting.
            if restart:
                newpid = start_runner(qrname, slice, count)
                kids[newpid] = (qrname, slice, count, restarts)
    finally:
        # Should we leave the main loop for any reason, we want to be sure
        # all of our children are exited cleanly.  Send SIGTERMs to all
        # the child processes and wait for them all to exit.
        for pid in kids:
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError, error:
                if error.errno == errno.ESRCH:
                    # The child has already exited.
                    log.info('ESRCH on pid: %d', pid)
        # Wait for all the children to go away.
        while True:
            try:
                pid, status = os.wait()
            except OSError, e:
                if e.errno == errno.ECHILD:
                    break
                elif e.errno == errno.EINTR:
                    continue
                raise



def main():
    """Main process."""
    global log, parser

    parser = parseargs()
    initialize(parser.options.config)

    # We can't grab the logger until after everything's been initialized.
    log = logging.getLogger('mailman.qrunner')

    # Acquire the master lock, exiting if we can't acquire it.  We'll let the
    # caller handle any clean up or lock breaking.
    with lockfile.Lock(config.LOCK_FILE, LOCK_LIFETIME) as lock:
        with open(config.PIDFILE, 'w') as fp:
            print >> fp, os.getpid()
        try:
            control_loop(lock)
        finally:
            os.remove(config.PIDFILE)



if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
