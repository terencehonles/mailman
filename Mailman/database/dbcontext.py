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

import os
import logging
import weakref

from sqlalchemy import BoundMetaData, create_session
from string import Template
from urlparse import urlparse

from Mailman import Version
from Mailman.configuration import config
from Mailman.database import address
from Mailman.database import languages
from Mailman.database import listdata
from Mailman.database import version
from Mailman.database.txnsupport import txn



class MlistRef(weakref.ref):
    def __init__(self, mlist, callback):
        super(MlistRef, self).__init__(mlist, callback)
        self.fqdn_listname = mlist.fqdn_listname


class Tables(object):
    def bind(self, table, attrname=None):
        if attrname is None:
            attrname = table.name.lower()
        setattr(self, attrname, table)



class DBContext(object):
    def __init__(self):
        self.tables = Tables()
        self.metadata = None
        self.session = None
        # Special transaction used only for MailList.Lock() .Save() and
        # .Unlock() interface.
        self._mlist_txns = {}

    def connect(self):
        # Calculate the engine url
        url = Template(config.SQLALCHEMY_ENGINE_URL).safe_substitute(
            config.paths)
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
        self._touch(url)
        self.metadata = BoundMetaData(url)
        self.metadata.engine.echo = config.SQLALCHEMY_ECHO
        # Create all the table objects, and then let SA conditionally create
        # them if they don't yet exist.  NOTE: this order matters!
        for module in (languages, address, listdata, version):
            module.make_table(self.metadata, self.tables)
        self.metadata.create_all()
        # Validate schema version, updating if necessary (XXX)
        r = self.tables.version.select(
            self.tables.version.c.component=='schema').execute()
        row = r.fetchone()
        if row is None:
            # Database has not yet been initialized
            self.tables.version.insert().execute(
                component='schema',
                version=Version.DATABASE_SCHEMA_VERSION)
        elif row.version <> Version.DATABASE_SCHEMA_VERSION:
            # XXX Update schema
            raise SchemaVersionMismatchError(row.version)
        self.session = create_session()

    def close(self):
        self.session.close()
        self.session = None

    def _touch(self, url):
        parts = urlparse(url)
        # XXX Python 2.5; use parts.scheme and parts.path
        if parts[0] <> 'sqlite':
            return
        path = os.path.normpath(parts[2])
        fd = os.open(path, os.O_WRONLY |  os.O_NONBLOCK | os.O_CREAT, 0666)
        # Ignore errors
        if fd > 0:
            os.close(fd)

    # Cooperative method for use with @txn decorator
    def _withtxn(self, meth, *args, **kws):
        try:
            txn = self.session.create_transaction()
            rtn = meth(*args, **kws)
        except:
            txn.rollback()
            raise
        else:
            txn.commit()
            return rtn

    def _unlock_mref(self, mref):
        txn = self._mlist_txns.pop(mref.fqdn_listname, None)
        if txn is not None:
            txn.rollback()

    # Higher level interface
    def api_lock(self, mlist):
        # Don't try to re-lock a list
        if mlist.fqdn_listname in self._mlist_txns:
            return
        txn = self.session.create_transaction()
        mref = MlistRef(mlist, self._unlock_mref)
        # If mlist.host_name is changed, its fqdn_listname attribute will no
        # longer match, so its transaction will not get committed when the
        # list is saved.  To avoid this, store on the mlist object the key
        # under which its transaction is stored.
        txnkey = mlist._txnkey = mlist.fqdn_listname
        self._mlist_txns[txnkey] = txn

    def api_unlock(self, mlist):
        try:
            txnkey = mlist._txnkey
        except AttributeError:
            return
        txn = self._mlist_txns.pop(txnkey, None)
        if txn is not None:
            txn.rollback()
        del mlist._txnkey

    def api_load(self, mlist):
        # Mark the MailList object such that future attribute accesses will
        # refresh from the database.
        self.session.expire(mlist)

    def api_save(self, mlist):
        # When dealing with MailLists, .Save() will always be followed by
        # .Unlock().  However lists can also be unlocked without saving.  But
        # if it's been locked it will always be unlocked.  So the rollback in
        # unlock will essentially be no-op'd if we've already saved the list.
        try:
            txnkey = mlist._txnkey
        except AttributeError:
            return
        txn = self._mlist_txns.pop(txnkey, None)
        if txn is not None:
            txn.commit()

    @txn
    def api_add_list(self, mlist):
        self.session.save(mlist)

    @txn
    def api_remove_list(self, mlist):
        self.session.delete(mlist)

    @txn
    def api_find_list(self, listname, hostname):
        from Mailman.MailList import MailList
        q = self.session.query(MailList)
        mlists = q.select_by(list_name=listname, host_name=hostname)
        assert len(mlists) <= 1, 'Duplicate mailing lists!'
        if mlists:
            return mlists[0]
        return None

    @txn
    def api_get_list_names(self):
        table = self.tables.listdata
        results = table.select().execute()
        return [(row[table.c.list_name], row[table.c.host_name])
                for row in results.fetchall()]



dbcontext = DBContext()
