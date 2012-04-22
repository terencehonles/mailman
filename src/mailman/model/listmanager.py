# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""A mailing list manager."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'ListManager',
    ]


from zope.event import notify
from zope.interface import implements

from mailman.database.transaction import dbconnection
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.listmanager import (
    IListManager, ListAlreadyExistsError, ListCreatedEvent, ListCreatingEvent,
    ListDeletedEvent, ListDeletingEvent)
from mailman.model.mailinglist import MailingList
from mailman.utilities.datetime import now



class ListManager:
    """An implementation of the `IListManager` interface."""

    implements(IListManager)

    @dbconnection
    def create(self, store, fqdn_listname):
        """See `IListManager`."""
        listname, at, hostname = fqdn_listname.partition('@')
        if len(hostname) == 0:
            raise InvalidEmailAddressError(fqdn_listname)
        notify(ListCreatingEvent(fqdn_listname))
        mlist = store.find(
            MailingList,
            MailingList.list_name == listname,
            MailingList.mail_host == hostname).one()
        if mlist:
            raise ListAlreadyExistsError(fqdn_listname)
        mlist = MailingList(fqdn_listname)
        mlist.created_at = now()
        store.add(mlist)
        notify(ListCreatedEvent(mlist))
        return mlist

    @dbconnection
    def get(self, store, fqdn_listname):
        """See `IListManager`."""
        listname, at, hostname = fqdn_listname.partition('@')
        return store.find(MailingList,
                          list_name=listname,
                          mail_host=hostname).one()

    @dbconnection
    def delete(self, store, mlist):
        """See `IListManager`."""
        fqdn_listname = mlist.fqdn_listname
        notify(ListDeletingEvent(mlist))
        store.remove(mlist)
        notify(ListDeletedEvent(fqdn_listname))

    @property
    @dbconnection
    def mailing_lists(self, store):
        """See `IListManager`."""
        for mlist in store.find(MailingList):
            yield mlist

    @dbconnection
    def __iter__(self, store):
        """See `IListManager`."""
        for mlist in store.find(MailingList):
            yield mlist

    @property
    @dbconnection
    def names(self, store):
        """See `IListManager`."""
        result_set = store.find(MailingList)
        for mail_host, list_name in result_set.values(MailingList.mail_host,
                                                      MailingList.list_name):
            yield '{0}@{1}'.format(list_name, mail_host)

    @property
    @dbconnection
    def name_components(self, store):
        """See `IListManager`."""
        result_set = store.find(MailingList)
        for mail_host, list_name in result_set.values(MailingList.mail_host,
                                                      MailingList.list_name):
            yield list_name, mail_host
