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


"""Portable (?) file locking with timeouts.  

This code should work with all versions of NFS.  The algorithm was suggested
by the GNU/Linux open() man page.  Make sure no malicious people have access
to link() to the lock file.
"""

import socket, os, time
import string
import errno
#from stat import ST_NLINK
ST_NLINK = 3                                      # faster


# default intervals are both specified in seconds, and can be floating point
# values.  DEFAULT_HUNG_TIMEOUT specifies the default length of time that a
# lock is expecting to hold the lock -- this can be set in the constructor, or 
# changed via a mutator.  DEFAULT_SLEEP_INTERVAL is the amount of time to
# sleep before checking the lock's status, if we were not the winning claimant 
# the previous time around.
DEFAULT_LOCK_LIFETIME   = 15
DEFAULT_SLEEP_INTERVAL = .25



# exceptions which can be raised
class LockError(Exception):
    """Base class for all exceptions in this module."""
    pass

class AlreadyLockedError(LockError):
    """Raised when a lock is attempted on an already locked object."""
    pass

class NotLockedError(LockError):
    """Raised when an unlock is attempted on an objec that isn't locked."""
    pass

class TimeOutError(LockError):
    """Raised when a lock was attempted, but did not succeed in the given
    amount of time.
    """
    pass

class StaleLockFileError(LockError):
    """Raised when a stale hardlink lock file was found."""
    pass



class LockFile:
    """A portable way to lock resources by way of the file system."""
    def __init__(self, lockfile,
                 lifetime=DEFAULT_LOCK_LIFETIME,
                 sleep_interval=DEFAULT_SLEEP_INTERVAL):
        """Creates a lock file using the specified file.

        lifetime is the maximum length of time expected to keep this lock.
        This value is written into the lock file so that other claimants on
        the lock know when it is safe to steal the lock, should the lock
        holder be wedged.

        sleep_interval is how often to wake up and check the lock file

        """
        self.__lockfile = lockfile
        self.__lifetime = lifetime
        self.__sleep_interval = sleep_interval
        self.__tmpfname = "%s.%s.%d" % (lockfile,
                                        socket.gethostname(),
                                        os.getpid())
        self.__kickstart()

    def set_lifetime(self, lifetime):
        """Reset the lifetime of the lock.
        Takes affect the next time the file is locked.
        """
        self.__lifetime = lifetime

    def refresh(self, newlifetime=None):
        """Refresh the lock.

        This writes a new release time into the lock file.  Use this if a
        process suddenly realizes it needs more time to do its work.  With
        optional newlifetime, this resets the lock lifetime value too.

        NotLockedError is raised if we don't already own the lock.
        """
        if not self.locked():
            raise NotLockedError
        if newlifetime is not None:
            self.set_lifetime(newlifetime)
        self.__write()

    def __del__(self):
        if self.locked():
            self.unlock()

    def __kickstart(self, force=0):
        # forcing means to remove the original lock file, and create a new
        # one.  this might be necessary if the file contains bogus locker
        # information such that the owner of the lock can't be determined
        if force:
            try:
                os.unlink(self.__lockfile)
            except IOError:
                pass
        if not os.path.exists(self.__lockfile):
            try:
                # make sure it's group writable
                oldmask = os.umask(002)
                try:
                    file = open(self.__lockfile, 'w+')
                    file.close()
                finally:
                    os.umask(oldmask)
            except IOError:
                pass

    def __write(self):
        # we expect to release our lock some time in the future.  we want to
        # give other claimants some clue as to when we think we're going to be
        # done with it, so they don't try to steal it out from underneath us
        # unless we've actually been wedged.
        lockrelease = time.time() + self.__lifetime
        # make sure it's group writable
        oldmask = os.umask(002)
        try:
            fp = open(self.__tmpfname, 'w')
            fp.write('%d %s %f\n' % (os.getpid(),
                                     self.__tmpfname,
                                     lockrelease))
            fp.close()
        finally:
            os.umask(oldmask)

    def __read(self):
        # can raise ValueError in two situations:
        #
        # either first element wasn't an integer (a valid pid), or we didn't
        # get a sequence of the right size from the string.split.  Either way,
        # the data in the file is bogus, but this is caught and handled higher
        # up.
        fp = open(self.__tmpfname, 'r')
        try:
            pid, winner, lockrelease = string.split(string.strip(fp.read()))
        finally:
            fp.close()
        return int(pid), winner, float(lockrelease)

    # Note that no one new can grab the lock once we've opened our tmpfile
    # until we close it, even if we don't have the lock.  So checking the PID
    # and stealing the lock are guaranteed to be atomic.
    def lock(self, timeout=0):
        """Blocks until the lock can be obtained.

        Raises a TimeOutError exception if a positive timeout value is given
        and that time elapses before the lock is obtained.

        This can possibly steal the lock from some other claimant, if the lock 
        lifetime that was written to the file has been exceeded.  Note that
        for this to work across machines, the clocks must be sufficiently
        synchronized.

        """
        if timeout > 0:
            timeout_time = time.time() + timeout
        last_pid = -1
        if self.locked():
            raise AlreadyLockedError
        stolen = 0
        while 1:
            # create the hard link and test for exactly 2 links to the file
            os.link(self.__lockfile, self.__tmpfname)
            if os.stat(self.__tmpfname)[ST_NLINK] == 2:
                # we have the lock (since there are no other links to the lock
                # file), so we can piss on the hydrant
                self.__write()
                break
            # we didn't get the lock this time.  let's see if we timed out
            if timeout and timeout_time < time.time():
                os.unlink(self.__tmpfname)
                raise TimeOutError
            # someone else must have gotten the lock.  let's find out who it
            # is.  if there is some bogosity in the lock file's data then we
            # will steal the lock.
            try:
                pid, winner, lockrelease = self.__read()
            except ValueError:
                os.unlink(self.__tmpfname)
                self.__kickstart(force=1)
                continue
            # If we've gotten to here, we should not be the winner, because
            # otherwise, an AlreadyCalledLockError should have been raised
            # above, and we should have never gotten into this loop.  However, 
            # the following scenario can occur, and this is what the stolen
            # flag takes care of:
            #
            # Say that processes A and B are already laying claim to the lock
            # by creating link files, and say A actually has the lock (i.e., A
            # is the winner).  We are process C and we lay claim by creating a
            # link file.  All is cool, and we'll trip the pid <> last_pid test
            # below, unlink our claim, sleep and try again.  Second time
            # through our loop, we again determine that A is the winner but
            # because it and B are swapped out, we trip our lifetime test
            # and figure we need to steal the lock.  So we piss on the hydrant
            # (write our info into the lock file), unlink A's link file and go
            # around the loop again.  However, because B is still laying
            # claim, and we never knew it (since it wasn't the winner), we
            # again have 3 links to the lock file the next time through this
            # loop, and the assert will trip.
            #
            # The stolen flag alerts us that this has happened, but I still
            # worry that our logic might be flawed here.
            assert stolen or winner <> self.__tmpfname
            # record the identity of the previous winner.  lockrelease is the
            # expected time that the winner will release the lock by.  we
            # don't want to steal it until this interval has passed, otherwise 
            # we could steal the lock out from underneath that process.
            if pid <> last_pid:
                last_pid = pid
            # here's where we potentially steal the lock.  if the pid in the
            # lockfile hasn't changed by lockrelease (a fixed point in time),
            # then we assume that the locker crashed
            elif lockrelease < time.time():
                self.__write()                # steal
                stolen = 1
                try:
                    os.unlink(winner)
                except os.error:
                    # winner lockfile could be missing
                    pass
                try:
                    os.unlink(self.__tmpfname)
                except os.error, (code, msg):
                    # Let's say we stole the lock, but some other process's
                    # claim was never cleaned up, perhaps because it crashed
                    # before that could happen.  The test for acquisition of
                    # the lock above will fail because there will be more than
                    # one hard link to the main lockfile.  But we'll get here
                    # and winner==self.__tmpfname, so the unlink above will
                    # fail (we'll have deleted it twice).  We could just steal
                    # the lock, but there's no reliable way to clean up the
                    # stale hard link, so we raise an exception instead and
                    # let the human operator take care of the problem.
                    if code == errno.ENOENT:
                        raise StaleLockFileError(
                            'Stale lock file found linked to file: '
                            +self.__lockfile+' (requires '+
                            'manual intervention)')
                    else:
                        raise
                continue
            # okay, someone else has the lock, we didn't steal it, and our
            # claim hasn't timed out yet.  So let's wait a while for the owner
            # of the lock to give it up.  Unlink our claim to the lock and
            # sleep for a while, then try again
            os.unlink(self.__tmpfname)
            time.sleep(self.__sleep_interval)

    # This could error if the lock is stolen.  You must catch it.
    def unlock(self):
        """Unlock the lock.

        If we don't already own the lock (either because of unbalanced unlock
        calls, or because the lock was stolen out from under us), raise a
        NotLockedError.
        """
        if not self.locked():
            raise NotLockedError
        os.unlink(self.__tmpfname)

    def locked(self):
        """Returns 1 if we own the lock, 0 if we do not."""
        if not os.path.exists(self.__tmpfname):
            return 0
        try:
            pid, winner, lockrelease = self.__read()
        except ValueError:
            # the contents of the lock file was corrupted
            os.unlink(self.__tmpfname)
            self.__kickstart(force=1)
            return 0
        return pid == os.getpid()

    # use with caution!!!
    def steal(self):
        """Explicitly steal the lock.  USE WITH CAUTION!"""
        self.__write()
