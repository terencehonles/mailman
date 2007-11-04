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

__metaclass__ = type
__all__ = [
    'StockDatabase',
    'flush', # for test convenience
    ]

import os

from locknix.lockfile import Lock
from storm.properties import PropertyPublisherMeta
from zope.interface import implements

from Mailman.interfaces import IDatabase
from Mailman.database.listmanager import ListManager
from Mailman.database.usermanager import UserManager
from Mailman.database.messagestore import MessageStore

# Test suite convenience.  Application code should use config.db.flush()
# instead.
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
        self.message_store = None
        self.pendings = None
        self.requests = None
        self._store = None

    def initialize(self, debug=None):
        # Avoid circular imports.
        from Mailman.configuration import config
        from Mailman.database import model
        from Mailman.database.model import Pendings
        from Mailman.database.model import Requests
        # Serialize this so we don't get multiple processes trying to create
        # the database at the same time.
        with Lock(os.path.join(config.LOCK_DIR, 'dbcreate.lck')):
            self.store = model.initialize(debug)
        self.list_manager = ListManager()
        self.user_manager = UserManager()
        self.message_store = MessageStore()
        self.pendings = Pendings()
        self.requests = Requests()

    def flush(self):
        pass

    def _reset(self):
        for model_class in _class_registry:
            for row in self.store.find(model_class):
                self.store.remove(row)



_class_registry = set()


class ModelMeta(PropertyPublisherMeta):
    """Do more magic on table classes."""

    def __init__(self, name, bases, dict):
        # Before we let the base class do it's thing, force an __storm_table__
        # property to enforce our table naming convention.
        self.__storm_table__ = name.lower()
        super(ModelMeta, self).__init__(name, bases, dict)
        # Register the model class so that it can be more easily cleared.
        # This is required by the test framework.
        if name == 'Model':
            return
        _class_registry.add(self)


class Model(object):
    """Like Storm's `Storm` subclass, but with a bit extra."""
    __metaclass__ = ModelMeta
