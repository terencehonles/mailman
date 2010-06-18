# Copyright (C) 2009-2010 by the Free Software Foundation, Inc.
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

"""Module stuff."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'DomainCollection',
    ]


from operator import attrgetter

from zope.component import getUtility
from zope.interface import implements

from mailman.app.membership import add_member, delete_member
from mailman.core.constants import system_preferences
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.listmanager import IListManager, NoSuchListError
from mailman.interfaces.member import DeliveryMode
from mailman.interfaces.membership import ISubscriptionService



class SubscriptionService:
    """Subscription services for the REST API."""

    implements(ISubscriptionService)

    __name__ = 'members'

    def get_members(self):
        """See `ISubscriptionService`."""
        # XXX 2010-02-24 barry Clean this up.
        # lazr.restful requires the return value to be a concrete list.
        members = []
        address_of_member = attrgetter('address.address')
        list_manager = getUtility(IListManager)
        for fqdn_listname in sorted(list_manager.names):
            mailing_list = list_manager.get(fqdn_listname)
            members.extend(
                sorted(mailing_list.owners.members, key=address_of_member))
            members.extend(
                sorted(mailing_list.moderators.members, key=address_of_member))
            members.extend(
                sorted(mailing_list.members.members, key=address_of_member))
        return members

    def __iter__(self):
        for member in self.get_members():
            yield member

    def join(self, fqdn_listname, address,
             real_name= None, delivery_mode=None):
        """See `ISubscriptionService`."""
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            raise NoSuchListError(fqdn_listname)
        # Convert from string to enum.
        mode = (DeliveryMode.regular
                if delivery_mode is None
                else DeliveryMode(delivery_mode))
        if real_name is None:
            real_name, at, domain = address.partition('@')
            if len(at) == 0:
                # It can't possibly be a valid email address.
                raise InvalidEmailAddressError(address)
        # Because we want to keep the REST API simple, there is no password or
        # language given to us.  We'll use the system's default language for
        # the user's default language.  We'll set the password to None.  XXX
        # Is that a good idea?  Maybe we should set it to something else,
        # except that once we encode the password (as we must do to avoid
        # cleartext passwords in the database) we'll never be able to retrieve
        # it.
        #
        # Note that none of these are used unless the address is completely
        # new to us.
        return add_member(mlist, address, real_name, None, mode,
                          system_preferences.preferred_language)

    def leave(self, fqdn_listname, address):
        """See `ISubscriptionService`."""
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            raise NoSuchListError(fqdn_listname)
        # XXX for now, no notification or user acknowledgement.
        delete_member(mlist, address, False, False)
        return ''
