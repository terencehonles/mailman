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

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ListManager',
    ]


import datetime

from zope.event import notify
from zope.interface import implements

from mailman.config import config
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.listmanager import (
    IListManager, ListAlreadyExistsError, ListCreatedEvent, ListCreatingEvent,
    ListDeletedEvent, ListDeletingEvent)
from mailman.model.mailinglist import MailingList



class ListManager:
    """An implementation of the `IListManager` interface."""

    implements(IListManager)

    def create(self, fqdn_listname):
        """See `IListManager`."""
        listname, at, hostname = fqdn_listname.partition('@')
        if len(hostname) == 0:
            raise InvalidEmailAddressError(fqdn_listname)
        notify(ListCreatingEvent(fqdn_listname))
        mlist = config.db.store.find(
            MailingList,
            MailingList.list_name == listname,
            MailingList.mail_host == hostname).one()
        if mlist:
            raise ListAlreadyExistsError(fqdn_listname)
        mlist = MailingList(fqdn_listname)
        mlist.created_at = datetime.datetime.now()
        config.db.store.add(mlist)
        notify(ListCreatedEvent(mlist))
        return mlist

    def get(self, fqdn_listname):
        """See `IListManager`."""
        listname, at, hostname = fqdn_listname.partition('@')
        return config.db.store.find(MailingList,
                                    list_name=listname,
                                    mail_host=hostname).one()

    def delete(self, mlist):
        """See `IListManager`."""
        fqdn_listname = mlist.fqdn_listname
        notify(ListDeletingEvent(mlist))
        config.db.store.remove(mlist)
        notify(ListDeletedEvent(fqdn_listname))

    @property
    def mailing_lists(self):
        """See `IListManager`."""
        for mlist in config.db.store.find(MailingList):
            yield mlist

    def __iter__(self):
        """See `IListManager`."""
        for mlist in config.db.store.find(MailingList):
            yield mlist

    @property
    def names(self):
        """See `IListManager`."""
        result_set = config.db.store.find(MailingList)
        for mail_host, list_name in result_set.values(MailingList.mail_host, 
                                                      MailingList.list_name):
            yield '{0}@{1}'.format(list_name, mail_host)

    @property
    def name_components(self):
        """See `IListManager`."""
        result_set = config.db.store.find(MailingList)
        for mail_host, list_name in result_set.values(MailingList.mail_host, 
                                                      MailingList.list_name):
            yield list_name, mail_host
