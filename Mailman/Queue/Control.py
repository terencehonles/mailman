# Copyright (C) 2001 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Main qrunner control routines.
"""

import sys
import os
import signal
import time
import errno

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import LockFile
from Mailman.Logging.Syslog import syslog

# Useful constants
LOCKFILE = os.path.join(mm_cfg.LOCK_DIR, 'master-qrunner')

# Since we wake up once per day and refresh the lock, the LOCK_LIFETIME
# needn't be (much) longer than SNOOZE.  We pad it 6 hours just to be safe.
LOCK_LIFETIME = mm_cfg.days(1) + mm_cfg.hours(6)
SNOOZE = mm_cfg.days(1)

# Global dictionary mapping child pids to (qrclass, slice, count)
KIDS = {}



# We want a SIGHUP to re-open all the log files.  By closing syslog, it will
# cause a new StampedLogger to be opened the next time a message is logged.
def sighup_handler(signum, frame):
    syslog.close()
    # SIGINT all the children so that they'll restart automatically.  Don't
    # kill the process group because we don't want ourselves to get the
    # signal!
    for pid in KIDS.keys():
        os.kill(pid, signal.SIGINT)
    # And just to tweak things...
    syslog('qrunner', 'qrunner caught SIGHUP.  Re-opening log files.')



def start_lock_refresher(lock):
    # This runs in its own subprocess, and it owns the global qrunner lock.
    pid = os.fork()
    if pid:
        # parent
        return pid
    # In the child, we simply wake up once per day and refresh the lock
    try:
        while 1:
            time.sleep(SNOOZE)
            lock.refresh()
    except KeyboardInterrupt:
        pass
    os._exit(0)



def start_runner(qrclass, slice, count):
    pid = os.fork()
    if pid:
        # parent
        syslog('qrunner', '%s qrunner started with pid: %d', qrclass, pid)
        return pid
    else:
        # child
        try:
            qrunner = qrclass(slice, count).run()
            syslog('qrunner', '%s qrunner exiting', qrclass)
        except KeyboardInterrupt:
            # Due to race conditions, the subproc could get the SIGINT inside
            # the syslog call.  It's of no consequence.
            pass
        os._exit(0)



def master(restart, lock):
    # Start up the lock refresher process
    watchdog_pid = start_lock_refresher(lock)
    # Start up all the qrunners
    for classname, count in mm_cfg.QRUNNERS:
        modulename = 'Mailman.Queue.' + classname
        __import__(modulename)
        qrclass = getattr(sys.modules[modulename], classname)
        for slice in range(count):
            info = (qrclass, slice, count)
            pid = start_runner(qrclass, slice, count)
            KIDS[pid] = info
    # Now just wait for children to end, but also catch KeyboardInterrupts
    if restart:
        restarting = '[restarting]'
    else:
        restarting = ''
    try:
        try:
            while 1:
                try:
                    pid, status = os.wait()
                except OSError, e:
                    if e.errno <> errno.EINTR: raise
                    # Just restart the wait()
                    continue
                killsig = status & 0xff
                exitstatus = (status >> 8) & 0xff
                # What should we do with this information other than log it?
                if pid == watchdog_pid:
                    syslog('qrunner', '''\
qrunner watchdog detected lock refresher exit
    (pid: %d, sig: %d, sts: %d) %s''', 
                           pid, killsig, exitstatus, restarting)
                    if restart:
                        watchdog_pid = start_lock_refresher(lock)
                else:
                    qrclass, slice, count = KIDS[pid]
                    syslog('qrunner', '''\
qrunner watchdog detected subprocess exit
    (pid: %d, sig: %d, sts: %d, class: %s, slice %d of %d) %s''',
                           pid, killsig, exitstatus, qrclass, slice, count,
                           restarting)
                    del KIDS[pid]
                    # Now perhaps restart the process
                    if restart:
                        newpid = start_runner(qrclass, slice, count)
                        KIDS[newpid] = (qrclass, slice, count)
        except KeyboardInterrupt:
            pass
    finally:
        # Should we leave the main loop for any reason, we want to be sure all
        # of our children are exited cleanly.  Send SIGINTs to all the child
        # processes and wait for them all to exit.  Include the watchdog!
        KIDS[watchdog_pid] = watchdog_pid
        for pid in KIDS.keys():
            try:
                os.kill(pid, signal.SIGINT)
            except OSError, e:
                if e.errno == errno.ESRCH:
                    # The child has already exited
                    del KIDS[pid]
        # Wait for all the children to go away
        Utils.reap(KIDS)



def start(restart, runner=None):
    """Main startup function.

    This is called by (the misnamed) cron/qrunner and by bin/mailmanctl.  If
    optional argument runner is provided, then the named qrunner is run once
    followed by a return of this function.  If runner is None, then we start
    the master qrunner main loop.
    """
    # Enable the SIGHUP handler
    signal.signal(signal.SIGHUP, sighup_handler)

    # Be sure we can acquire the master qrunner lock.  If not, it means some
    # other master qrunner daemon is already going.  This isn't allowed even
    # if we're doing a one-shot runner.  Allow the LockFile.TimeOutError to
    # propagate to the caller.
    lock = LockFile.LockFile(LOCKFILE, LOCK_LIFETIME)
    lock.lock(0.5)

    if runner is None:
        # Run master in the foreground, storing our own pid in the pid file
        fp = open(mm_cfg.PIDFILE, 'w')
        print >> fp, os.getpid()
        fp.close()
        try:
            master(restart, lock)
        finally:
            try:
                os.unlink(mm_cfg.PIDFILE)
            except EnvironmentError, e:
                if e.errno <> errno.ENOENT: raise
                # Otherwise ignore this
    else:
        # One-shot
        classname = runner + 'Runner'
        modulename = 'Mailman.Queue.%s' % classname
        # Let import errors percolate up
        __import__(modulename)
        class_ = getattr(sys.modules[modulename], classname)
        # Subclass to hack in the setting of the stop flag in the
        # _doperiodic() subclass.
        class Once(class_):
            def _doperiodic(self):
                self.stop()
        runner = Once()
        runner.run()
