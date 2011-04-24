# Copyright (C) 2009-2011 by the Free Software Foundation, Inc.
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
    'SubscriptionService',
    ]


from operator import attrgetter

from zope.component import getUtility
from zope.interface import implements

from mailman.app.membership import add_member, delete_member
from mailman.config import config
from mailman.core.constants import system_preferences
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.listmanager import IListManager, NoSuchListError
from mailman.interfaces.member import DeliveryMode
from mailman.interfaces.membership import (
    ISubscriptionService, MissingUserError)
from mailman.interfaces.usermanager import IUserManager
from mailman.model.member import Member
from mailman.utilities.passwords import make_user_friendly_password



class SubscriptionService:
    """Subscription services for the REST API."""

    implements(ISubscriptionService)

    __name__ = 'members'

    def get_members(self):
        """See `ISubscriptionService`."""
        # XXX 2010-02-24 barry Clean this up.
        # lazr.restful requires the return value to be a concrete list.
        members = []
        address_of_member = attrgetter('address.email')
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

    def get_member(self, member_id):
        """See `ISubscriptionService`."""
        members = config.db.store.find(
            Member,
            Member._member_id == member_id)
        if members.count() == 0:
            return None
        else:
            assert members.count() == 1, 'Too many matching members'
            return members[0]

    def __iter__(self):
        for member in self.get_members():
            yield member

    def join(self, fqdn_listname, subscriber,
             real_name= None, delivery_mode=None):
        """See `ISubscriptionService`."""
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            raise NoSuchListError(fqdn_listname)
        # Convert from string to enum.
        mode = (DeliveryMode.regular
                if delivery_mode is None
                else delivery_mode)
        # Is the subscriber a user or email address?
        if '@' in subscriber:
            # It's an email address, so we'll want a real name.
            if real_name is None:
                real_name, at, domain = subscriber.partition('@')
                if len(at) == 0:
                    # It can't possibly be a valid email address.
                    raise InvalidEmailAddressError(subscriber)
            # Because we want to keep the REST API simple, there is no
            # password or language given to us.  We'll use the system's
            # default language for the user's default language.  We'll set the
            # password to a system default.  This will have to get reset since
            # it can't be retrieved.  Note that none of these are used unless
            # the address is completely new to us.
            password = make_user_friendly_password()
            return add_member(mlist, subscriber, real_name, password, mode,
                              system_preferences.preferred_language)
        else:
            # We have to assume it's a user id.
            user = getUtility(IUserManager).get_user_by_id(subscriber)
            if user is None:
                raise MissingUserError(subscriber)
            return mlist.subscribe(user)

    def leave(self, fqdn_listname, address):
        """See `ISubscriptionService`."""
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            raise NoSuchListError(fqdn_listname)
        # XXX for now, no notification or user acknowledgement.
        delete_member(mlist, address, False, False)
        return ''
