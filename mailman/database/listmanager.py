# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""A mailing list manager."""

import datetime

from zope.interface import implements

from mailman import Errors
from mailman.Utils import split_listname, fqdn_listname
from mailman.configuration import config
from mailman.database.mailinglist import MailingList
from mailman.interfaces import IListManager, ListAlreadyExistsError



class ListManager(object):
    """An implementation of the `IListManager` interface."""

    implements(IListManager)

    def create(self, fqdn_listname):
        """See `IListManager`."""
        listname, hostname = split_listname(fqdn_listname)
        mlist = config.db.store.find(
            MailingList,
            MailingList.list_name == listname,
            MailingList.host_name == hostname).one()
        if mlist:
            raise ListAlreadyExistsError(fqdn_listname)
        mlist = MailingList(fqdn_listname)
        mlist.created_at = datetime.datetime.now()
        config.db.store.add(mlist)
        return mlist

    def get(self, fqdn_listname):
        """See `IListManager`."""
        listname, hostname = split_listname(fqdn_listname)
        mlist = config.db.store.find(MailingList,
                                     list_name=listname,
                                     host_name=hostname).one()
        if mlist is not None:
            # XXX Fixme
            mlist._restore()
        return mlist

    def delete(self, mlist):
        """See `IListManager`."""
        config.db.store.remove(mlist)

    @property
    def mailing_lists(self):
        """See `IListManager`."""
        for fqdn_listname in self.names:
            yield self.get(fqdn_listname)

    @property
    def names(self):
        """See `IListManager`."""
        for mlist in config.db.store.find(MailingList):
            yield fqdn_listname(mlist.list_name, mlist.host_name)
