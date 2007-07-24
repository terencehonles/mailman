# Copyright (C) 2006-2007 by the Free Software Foundation, Inc.
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

from elixir import objectstore
from zope.interface import implements

from Mailman.interfaces import IDatabase
from Mailman.database.listmanager import ListManager
from Mailman.database.usermanager import UserManager

__metaclass__ = type
__all__ = [
    'StockDatabase',
    'flush', # for test convenience
    ]

flush = None



class StockDatabase:
    implements(IDatabase)

    def __init__(self):
        # Expose the flush() method for test case convenience using the stock
        # database.
        global flush
        flush = self.flush
        self.list_manager = None
        self.user_manager = None

    def initialize(self):
        from Mailman.LockFile import LockFile
        from Mailman.configuration import config
        from Mailman.database import model
        # Serialize this so we don't get multiple processes trying to create the
        # database at the same time.
        lockfile = os.path.join(config.LOCK_DIR, '<dbcreatelock>')
        with LockFile(lockfile):
            model.initialize()
        self.list_manager = ListManager()
        self.user_manager = UserManager()
        self.flush()

    def flush(self):
        objectstore.flush()
