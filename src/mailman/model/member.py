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

"""Model for members."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Member',
    ]

from storm.locals import Int, Reference, Unicode
from storm.properties import UUID
from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.core.constants import system_preferences
from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.interfaces.action import Action
from mailman.interfaces.address import IAddress
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.member import IMember, MemberRole, MembershipError
from mailman.interfaces.user import IUser, UnverifiedAddressError
from mailman.interfaces.usermanager import IUserManager
from mailman.utilities.uid import UniqueIDFactory


uid_factory = UniqueIDFactory(context='members')



class Member(Model):
    implements(IMember)

    id = Int(primary=True)
    _member_id = UUID()
    role = Enum(MemberRole)
    mailing_list = Unicode()
    moderation_action = Enum(Action)

    address_id = Int()
    _address = Reference(address_id, 'Address.id')
    preferences_id = Int()
    preferences = Reference(preferences_id, 'Preferences.id')
    user_id = Int()
    _user = Reference(user_id, 'User.id')

    def __init__(self, role, mailing_list, subscriber):
        self._member_id = uid_factory.new_uid()
        self.role = role
        self.mailing_list = mailing_list
        if IAddress.providedBy(subscriber):
            self._address = subscriber
            # Look this up dynamically.
            self._user = None
        elif IUser.providedBy(subscriber):
            self._user = subscriber
            # Look this up dynamically.
            self._address = None
        else:
            raise ValueError('subscriber must be a user or address')
        if role in (MemberRole.owner, MemberRole.moderator):
            self.moderation_action = Action.accept
        elif role is MemberRole.member:
            self.moderation_action = getUtility(IListManager).get(
                mailing_list).default_member_action
        else:
            assert role is MemberRole.nonmember, (
                'Invalid MemberRole: {0}'.format(role))
            self.moderation_action = getUtility(IListManager).get(
                mailing_list).default_nonmember_action

    def __repr__(self):
        return '<Member: {0} on {1} as {2}>'.format(
            self.address, self.mailing_list, self.role)

    @property
    def member_id(self):
        """See `IMember`."""
        return self._member_id

    @property
    def address(self):
        """See `IMember`."""
        return (self._user.preferred_address
                if self._address is None
                else self._address)

    @address.setter
    def address(self, new_address):
        """See `IMember`."""
        if self._address is None:
            # XXX Either we need a better exception here, or we should allow
            # changing a subscription from preferred address to explicit
            # address (and vice versa via del'ing the .address attribute.
            raise MembershipError('Membership is via preferred address')
        if new_address.verified_on is None:
            # A member cannot change their subscription address to an
            # unverified address.
            raise UnverifiedAddressError(new_address)
        user = getUtility(IUserManager).get_user(new_address.email)
        if user is None or user != self.user:
            raise MembershipError('Address is not controlled by user')
        self._address = new_address

    @property
    def user(self):
        """See `IMember`."""
        return (self._user
                if self._address is None
                else getUtility(IUserManager).get_user(self._address.email))

    def _lookup(self, preference):
        pref = getattr(self.preferences, preference)
        if pref is not None:
            return pref
        pref = getattr(self.address.preferences, preference)
        if pref is not None:
            return pref
        if self.address.user:
            pref = getattr(self.address.user.preferences, preference)
            if pref is not None:
                return pref
        return getattr(system_preferences, preference)

    @property
    def acknowledge_posts(self):
        """See `IMember`."""
        return self._lookup('acknowledge_posts')

    @property
    def preferred_language(self):
        """See `IMember`."""
        return self._lookup('preferred_language')

    @property
    def receive_list_copy(self):
        """See `IMember`."""
        return self._lookup('receive_list_copy')

    @property
    def receive_own_postings(self):
        """See `IMember`."""
        return self._lookup('receive_own_postings')

    @property
    def delivery_mode(self):
        """See `IMember`."""
        return self._lookup('delivery_mode')

    @property
    def delivery_status(self):
        """See `IMember`."""
        return self._lookup('delivery_status')

    @property
    def options_url(self):
        """See `IMember`."""
        # XXX Um, this is definitely wrong
        return 'http://example.com/' + self.address.email

    def unsubscribe(self):
        """See `IMember`."""
        config.db.store.remove(self.preferences)
        config.db.store.remove(self)
