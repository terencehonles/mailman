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
    self.tmpfname = "%s.%s.%d" % (lockfile, socket.gethostname(), os.getpid())
    self.is_locked = 0
    if not os.path.exists(self.lockfile):
      try:
         file = open(self.lockfile, "w+")
      except IOError:
        pass

  # Note that no one new can grab the lock once we've opened our
  # tmpfile until we close it, even if we don't have the lock.  So
  # checking the PID and stealing the lock are garunteed to be atomic.
  def lock(self, timeout = 0):
    """Blocks until the lock can be obtained.  Raises a TimeOutError
       exception if a positive timeout value is given and that time
       elapses before the lock is obtained.
    """
    if timeout > 0:
      timeout_time = time.time() + timeout
    last_pid = -1
    if self.locked():
      raise AlreadyCalledLockError
    while 1:
      os.link(self.lockfile, self.tmpfname)
      if os.stat(self.tmpfname)[3] == 2:
        file = open(self.tmpfname, 'w+')
        file.write(`os.getpid(),self.tmpfname`)
        file.close()
        self.is_locked = 1
        break
      if timeout and timeout_time < time.time():
        raise TimeOutError
      file = open(self.tmpfname, 'r')
      try:
        pid,winner = eval(file.read())
      except SyntaxError: # no info in file... *can* happen
        file.close()
        os.unlink(self.tmpfname)
        continue
      file.close()
      if pid <> last_pid:
        last_pid = pid
        stime = time.time()
      if (stime + self.hung_timeout < time.time()) and self.hung_timeout > 0:
        file = open(self.tmpfname, 'w+')
    	file.write(`os.getpid(),self.tmpfname`)
        try:
          os.unlink(winner)
        except os.error:
          pass
        os.unlink(self.tmpfname)
        continue
      os.unlink(self.tmpfname)
      time.sleep(self.sleep_interval)
  # This could error if the lock is stolen.  You must catch it.
  def unlock(self):
    if not self.locked():
       raise NotLockedError
    self.is_locked = 0
    os.unlink(self.tmpfname)
  def locked(self):
    return os.path.exists(self.tmpfname) and self.is_locked