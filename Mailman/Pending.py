# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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

new(stuff...) places an item's data in the db, returning its cookie.

confirmed(cookie) returns a tuple for the data, removing the item
from the db.  It returns None if the cookie is not registered.
"""

import os
import time
import sha
import marshal
import random
import errno

from Mailman import mm_cfg
from Mailman import LockFile

DBFILE = os.path.join(mm_cfg.DATA_DIR, 'pending.db')
LOCKFILE = os.path.join(mm_cfg.LOCK_DIR, 'pending.lock')



def new(*content):
    """Create a new entry in the pending database, returning cookie for it."""
    # Acquire the pending database lock, letting TimeOutError percolate up.
    lock = LockFile.LockFile(LOCKFILE)
    lock.lock(timeout=30)
    try:
        # Load the current database
        db = _load()
        # Calculate a unique cookie
        while 1:
            n = random.random()
            now = time.time()
            hashfood = str(now) + str(n) + str(content)
            cookie = sha.new(hashfood).hexdigest()
            if not db.has_key(cookie):
                break
        # Store the content, plus the time in the future when this entry will
        # be evicted from the database, due to staleness.
        db[cookie] = content + (now + mm_cfg.PENDING_REQUEST_LIFE,)
        _save(db)
        return cookie
    finally:
        lock.unlock()



def confirm(cookie):
    """Return data for cookie, removing it from db, or None if not found."""
    # Acquire the pending database lock, letting TimeOutError percolate up.
    lock = LockFile.LockFile(LOCKFILE)
    lock.lock(timeout=30)
    try:
        # Load the database
        db = _load()
        missing = []
        content = db.get(cookie, missing)
        if content is missing:
            return None
        # Remove the entry from the database
        del db[cookie]
        _save(db)
        # Strip off the timestamp and return the data
        return content[:-1]
    finally:
        lock.unlock()



def _load():
    # Lock must be acquired.
    try:
        fp = open(DBFILE)
        return marshal.load(fp)
    except IOError, e:
        if e.errno <> errno.ENOENT: raise
        # No database yet, so initialize a fresh one
        return {}


def _save(db):
    # Lock must be acquired.
    now = time.time()
    for cookie, data in db.items():
        timestamp = data[-1]
        if now > timestamp:
            # The entry is stale, so remove it.
            del db[cookie]
    omask = os.umask(007)
    try:
        fp = open(DBFILE, 'w')
        marshal.dump(db, fp)
        fp.close()
    finally:
        os.umask(omask)



def _update(olddb):
    # Update an old pending database to the new database
    lock = LockFile.LockFile(LOCKFILE)
    lock.lock(timeout=30)
    try:
        # We don't need this entry anymore
        if olddb.has_key('lastculltime'):
            del olddb['lastculltime']
        db = _load()
        db.update(olddb)
        _save(db)
    finally:
        lock.unlock()
