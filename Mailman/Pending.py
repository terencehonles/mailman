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

""" Track pending confirmation of subscriptions.

Pending().new(stuff...) places an item's data in the db, returning its cookie.
Pending().confirmed(cookie) returns a tuple for the data, removing the item
from the db.  It returns None if the cookie is not registered.
"""

import os 
import marshal
import time
import whrandom
import mm_cfg
import flock

DB_PATH = os.path.join(mm_cfg.DATA_DIR, "pending_subscriptions.db")
LOCK_PATH = os.path.join(mm_cfg.LOCK_DIR, "pending_subscriptions.lock")
PENDING_REQUEST_LIFE = mm_cfg.PENDING_REQUEST_LIFE
# Something's probably wedged if we hit this.
DB_LOCK_TIMEOUT = 30
# Cull stale items from the db on save, after enough time since the last one:
CULL_INTERVAL = (mm_cfg.PENDING_REQUEST_LIFE / 10)

class Pending:
    """Db interface for tracking pending confirmations, using random cookies.

      .new(stuff...) places an item's data in the db, returning its cookie.
      .confirmed(cookie) returns a tuple for the data, removing item from db.

    The db is occasionally culled for stale items during saves."""
    # The db is a marshalled dict with two kinds of entries; a bunch of:
    #   cookie: (content..., timestamp)
    # and just one:
    #   LAST_CULL_KEY: next_cull_due_time
    # Dbs lacking the LAST_CULL_KEY are culled, at which point the cull key 
    # is added.
    LAST_CULL_KEY = "lastculltime"
    def __init__(self,
               db_path = DB_PATH,
               lock_path = LOCK_PATH,
               item_life = PENDING_REQUEST_LIFE,
               cull_interval = CULL_INTERVAL,
               db_lock_timeout = DB_LOCK_TIMEOUT):
        self.item_life = item_life
        self.db_path = db_path
        self.__lock = flock.FileLock(lock_path)
        self.cull_interval = cull_interval
        self.db_lock_timeout = db_lock_timeout
    def new(self, *content):
        """Create a new entry in the pending db, returning cookie for it."""
        now = int(time.time())
        db = self.__load()
        # Generate cookie between 1e5 and 1e6 and not already in the db.
        while 1:
            newcookie = int(whrandom.random() * 1e6)
            if newcookie >= 1e5 and not db.has_key(newcookie):
                break
        db[newcookie] = content + (now,) # Tack on timestamp.
        self.__save(db)
        return newcookie
    def confirmed(self, cookie):
        "Return entry for cookie, removing it from db, or None if not found."
        content = None
        got = None
        db = self.__load()
        try:
            if db.has_key(cookie):
                content = db[cookie][0:-1] # Strip off timestamp.
                got = 1
                del db[cookie]
        finally:
            if got:
                self.__save(db)
            else:
                self.__release_lock()
        return content
    def __load(self):
        "Return db as dict, returning an empty one if db not yet existant."
        self.__assert_lock(self.db_lock_timeout)
        try:
            fp = open(self.db_path,"r" )
            return marshal.load(fp)
        except IOError:
            # Not yet existing Initialize a fresh one:
            return {self.LAST_CULL_KEY: int(time.time())}
    def __save(self, db):
        """Marshal dict db to file - the exception is propagated on failure.
        Cull stale items from the db, if that hasn't been done in a while."""
        if not self.__lock.locked():
            raise flock.NotLockedError
        # Cull if its been a while (or if cull key is missing, ie, old
        # version - which will be reformed to new format by cull).
        if (db.get(self.LAST_CULL_KEY, 0)
            < int(time.time()) - self.cull_interval):
            self.__cull_db(db)
        fp = open(self.db_path, "w") 
        marshal.dump(db, fp) 
        fp.close()
        self.__release_lock()
    def __assert_lock(self, timeout):
        """Get the lock if not already acquired, or happily just keep it.

        Raises TimeOutError if unable to get lock within timeout."""
        try:
            self.__lock.lock(timeout)
        except flock.AlreadyCalledLockError:
            pass
    def __release_lock(self):
        self.__lock.unlock()
    def __cull_db(self, db):
        """Remove old items from db and revise last-culled timestamp."""
        now = int(time.time())
        too_old = now - self.item_life
        cullkey = self.LAST_CULL_KEY
        for k, v in db.items():
            if k == cullkey:
                continue
            if v[-1] < too_old:
                del db[k]
        # Register time after which a new cull is due:
        db[self.LAST_CULL_KEY] = now
