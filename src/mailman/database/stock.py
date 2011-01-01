# Copyright (C) 2006-2011 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'StockDatabase',
    ]

import os
import logging

from flufl.lock import Lock
from lazr.config import as_boolean
from pkg_resources import resource_string
from storm.cache import GenerationalCache
from storm.locals import create_database, Store
from urlparse import urlparse
from zope.interface import implements

import mailman.version

from mailman.config import config
from mailman.interfaces.database import IDatabase, SchemaVersionMismatchError
from mailman.model.version import Version
from mailman.utilities.string import expand

log = logging.getLogger('mailman.config')



class StockDatabase:
    """The standard database, using Storm on top of SQLite."""

    implements(IDatabase)

    def __init__(self):
        self.url = None
        self.store = None

    def initialize(self, debug=None):
        """See `IDatabase`."""
        # Serialize this so we don't get multiple processes trying to create
        # the database at the same time.
        with Lock(os.path.join(config.LOCK_DIR, 'dbcreate.lck')):
            self._create(debug)

    def begin(self):
        """See `IDatabase`."""
        # Storm takes care of this for us.
        pass

    def commit(self):
        """See `IDatabase`."""
        self.store.commit()

    def abort(self):
        """See `IDatabase`."""
        self.store.rollback()

    def _create(self, debug):
        # Calculate the engine url.
        url = expand(config.database.url, config.paths)
        log.debug('Database url: %s', url)
        # XXX By design of SQLite, database file creation does not honor
        # umask.  See their ticket #1193:
        # http://www.sqlite.org/cvstrac/tktview?tn=1193,31
        #
        # This sucks for us because the mailman.db file /must/ be group
        # writable, however even though we guarantee our umask is 002 here, it
        # still gets created without the necessary g+w permission, due to
        # SQLite's policy.  This should only affect SQLite engines because its
        # the only one that creates a little file on the local file system.
        # This kludges around their bug by "touch"ing the database file before
        # SQLite has any chance to create it, thus honoring the umask and
        # ensuring the right permissions.  We only try to do this for SQLite
        # engines, and yes, we could have chmod'd the file after the fact, but
        # half dozen and all...
        self.url = url
        touch(url)
        database = create_database(url)
        store = Store(database, GenerationalCache())
        database.DEBUG = (as_boolean(config.database.debug)
                          if debug is None else debug)
        # Check the sqlite master database to see if the version file exists.
        # If so, then we assume the database schema is correctly initialized.
        # Storm does not currently have schema creation.  This is not an ideal
        # way to handle creating the database, but it's cheap and easy for
        # now.
        table_names = [item[0] for item in 
                       store.execute('select tbl_name from sqlite_master;')]
        if 'version' not in table_names:
            # Initialize the database.
            sql = resource_string('mailman.database', 'mailman.sql')
            for statement in sql.split(';'):
                store.execute(statement + ';')
        # Validate schema version.
        v = store.find(Version, component='schema').one()
        if not v:
            # Database has not yet been initialized
            v = Version(component='schema',
                        version=mailman.version.DATABASE_SCHEMA_VERSION)
            store.add(v)
        elif v.version <> mailman.version.DATABASE_SCHEMA_VERSION:
            # XXX Update schema
            raise SchemaVersionMismatchError(v.version)
        self.store = store
        store.commit()

    def _reset(self):
        """See `IDatabase`."""
        from mailman.database.model import ModelMeta
        self.store.rollback()
        ModelMeta._reset(self.store)



def touch(url):
    parts = urlparse(url)
    if parts.scheme <> 'sqlite':
        return
    path = os.path.normpath(parts.path)
    fd = os.open(path, os.O_WRONLY |  os.O_NONBLOCK | os.O_CREAT, 0666)
    # Ignore errors
    if fd > 0:
        os.close(fd)
