# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

from Mailman import Errors
from Mailman.Utils import split_listname, fqdn_listname
from Mailman.configuration import config
from Mailman.database.mailinglist import MailingList
from Mailman.interfaces import IListManager



class ListManager(object):
    implements(IListManager)

    def create(self, fqdn_listname):
        listname, hostname = split_listname(fqdn_listname)
        mlist = config.db.store.find(
            MailingList,
            MailingList.list_name == listname,
            MailingList.host_name == hostname).one()
        if mlist:
            raise Errors.MMListAlreadyExistsError(fqdn_listname)
        mlist = MailingList(fqdn_listname)
        mlist.created_at = datetime.datetime.now()
        config.db.store.add(mlist)
        return mlist

    def delete(self, mlist):
        config.db.store.remove(mlist)

    def get(self, fqdn_listname):
        listname, hostname = split_listname(fqdn_listname)
        mlist = config.db.store.find(MailingList,
                                     list_name=listname,
                                     host_name=hostname).one()
        if mlist is not None:
            # XXX Fixme
            mlist._restore()
        return mlist

    @property
    def mailing_lists(self):
        # Don't forget, the MailingList objects that this class manages must
        # be wrapped in a MailList object as expected by this interface.
        for fqdn_listname in self.names:
            yield self.get(fqdn_listname)

    @property
    def names(self):
        for mlist in config.db.store.find(MailingList):
            yield fqdn_listname(mlist.list_name, mlist.host_name)
