# Copyright (C) 1998 by the Free Software Foundation, Inc.
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
#
# flock.py: Portable file locking.  John Viega, Jun 13, 1998


"""Portable (?) file locking with timeouts.  
This code should work with all versions of NFS.
The algorithm was suggested by the GNU/Linux open() man page.  Make
sure no malicious people have access to link() to the lock file.
"""

# Potential change: let the locker insert a field saying when he promises
# to be done with the lock, so if he needs more time than the other
# processes think he needs, he can say so.

import socket, os, time
import string
#from stat import ST_NLINK
ST_NLINK = 3                                      # faster

DEFAULT_HUNG_TIMEOUT   = 15
DEFAULT_SLEEP_INTERVAL = .25

AlreadyCalledLockError = "AlreadyCalledLockError"
NotLockedError         = "NotLockedError"
TimeOutError           = "TimeOutError"


class FileLock:
    def __init__(self, lockfile, hung_timeout = DEFAULT_HUNG_TIMEOUT,
                 sleep_interval = DEFAULT_SLEEP_INTERVAL):
        self.lockfile = lockfile
        self.hung_timeout = hung_timeout
        self.sleep_interval = sleep_interval
        self.tmpfname = "%s.%s.%d" % (lockfile, socket.gethostname(),
                                      os.getpid())
        self.__kickstart()

    def __del__(self):
        if self.locked():
            self.unlock()

    def __kickstart(self, force=0):
        # forcing means to remove the original lockfile, and create a new one.
        # this might be necessary if the file contains bogus locker
        # information such that the owner of the lock can't be determined
        if force:
            try:
                os.unlink(self.lockfile)
            except IOError:
                pass
        if not os.path.exists(self.lockfile):
            try:
                # make sure it's group writable
                oldmask = os.umask(002)
                try:
                    file = open(self.lockfile, 'w+')
                    file.close()
                finally:
                    os.umask(oldmask)
            except IOError:
                pass

    def __write(self):
        # make sure it's group writable
        oldmask = os.umask(002)
        try:
            fp = open(self.tmpfname, 'w')
            fp.write('%d %s\n' % (os.getpid(), self.tmpfname))
            fp.close()
        finally:
            os.umask(oldmask)

    def __read(self):
        # can raise ValueError in two situations:
        #
        # either first element wasn't an integer (a valid pid), or we didn't
        # get a 2-list from the string.split.  Either way, the data in the
        # file is bogus, but this is caught higher up
        fp = open(self.tmpfname, 'r')
        try:
            pid, winner = string.split(string.strip(fp.read()))
        finally:
            fp.close()
        return int(pid), winner

    # Note that no one new can grab the lock once we've opened our tmpfile
    # until we close it, even if we don't have the lock.  So checking the PID
    # and stealing the lock are guaranteed to be atomic.
    def lock(self, timeout = 0):
        """Blocks until the lock can be obtained.

        Raises a TimeOutError exception if a positive timeout value is given
        and that time elapses before the lock is obtained.

        """
        if timeout > 0:
            timeout_time = time.time() + timeout
        last_pid = -1
        if self.locked():
            raise AlreadyCalledLockError
        while 1:
            # create the hard link and test for exactly 2 links to the file
            os.link(self.lockfile, self.tmpfname)
            if os.stat(self.tmpfname)[ST_NLINK] == 2:
                # we have the lock (since there are no other links to the lock
                # file), so we can piss on the hydrant
                self.__write()
                break
            if timeout and timeout_time < time.time():
                raise TimeOutError
            # someone else must have gotten the lock.  let's find out who it
            # is.  if there is some bogosity in the lock file's data then we
            # will steal the lock.
            try:
                pid, winner = self.__read()
            except ValueError:
                os.unlink(self.tmpfname)
                self.__kickstart(force=1)
                continue
            assert winner <> self.tmpfname
            # record the previous winner and the current time
            if pid <> last_pid:
                last_pid = pid
                stime = time.time()
            # here's where we potentially steal the lock.  if the pid in the
            # lockfile hasn't changed in hung_timeout seconds, then we assume
            # that the locker crashed
            elif stime + self.hung_timeout < time.time():
                self.__write()                    # steal
                try:
                    os.unlink(winner)
                except os.error:
                    # winner lockfile could be missing
                    pass
                os.unlink(self.tmpfname)
                continue
            # okay, someone else has the lock, we didn't steal it, and it
            # hasn't timed out yet.  So let's wait for the owner of the lock
            # to give it up.  Unlink our claim to the lock and sleep for a
            # while, then try again
            os.unlink(self.tmpfname)
            time.sleep(self.sleep_interval)

    # This could error if the lock is stolen.  You must catch it.
    def unlock(self):
        if not self.locked():
            raise NotLockedError
        os.unlink(self.tmpfname)

    def locked(self):
        if not os.path.exists(self.tmpfname):
            return 0
        pid, winner = self.__read()
        return pid == os.getpid()
