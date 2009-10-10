# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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

from zope.interface import implements

from mailman.config import config
from mailman.core.errors import InvalidEmailAddress
from mailman.interfaces.listmanager import IListManager, ListAlreadyExistsError
from mailman.interfaces.rest import IResolvePathNames
from mailman.model.mailinglist import MailingList



class ListManager:
    """An implementation of the `IListManager` interface."""

    implements(IListManager, IResolvePathNames)

    # pylint: disable-msg=R0201
    def create(self, fqdn_listname):
        """See `IListManager`."""
        listname, at, hostname = fqdn_listname.partition('@')
        if len(hostname) == 0:
            raise InvalidEmailAddress(fqdn_listname)
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
        listname, at, hostname = fqdn_listname.partition('@')
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
            yield '{0}@{1}'.format(mlist.list_name, mlist.host_name)

    def get_mailing_lists(self):
        """See `IListManager`."""
        # lazr.restful will not allow this to be a generator.
        return list(self.mailing_lists)

    def new(self, fqdn_listname):
        """See `IListManager."""
        from mailman.app.lifecycle import create_list
        return create_list(fqdn_listname)
