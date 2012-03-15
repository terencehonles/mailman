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

"""Model for users."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'User',
    ]

from storm.locals import (
    DateTime, Int, RawStr, Reference, ReferenceSet, Unicode)
from storm.properties import UUID
from zope.interface import implements

from mailman.config import config
from mailman.database.model import Model
from mailman.interfaces.address import (
    AddressAlreadyLinkedError, AddressNotLinkedError)
from mailman.interfaces.user import IUser, UnverifiedAddressError
from mailman.model.address import Address
from mailman.model.preferences import Preferences
from mailman.model.roster import Memberships
from mailman.utilities.datetime import factory as date_factory
from mailman.utilities.uid import UniqueIDFactory


uid_factory = UniqueIDFactory(context='users')



class User(Model):
    """Mailman users."""

    implements(IUser)

    id = Int(primary=True)
    display_name = Unicode()
    password = RawStr()
    _user_id = UUID()
    _created_on = DateTime()

    addresses = ReferenceSet(id, 'Address.user_id')
    _preferred_address_id = Int()
    _preferred_address = Reference(_preferred_address_id, 'Address.id')
    preferences_id = Int()
    preferences = Reference(preferences_id, 'Preferences.id')

    def __init__(self, display_name=None, preferences=None):
        super(User, self).__init__()
        self._created_on = date_factory.now()
        user_id = uid_factory.new_uid()
        assert config.db.store.find(User, _user_id=user_id).count() == 0, (
            'Duplicate user id {0}'.format(user_id))
        self._user_id = user_id
        self.display_name = ('' if display_name is None else display_name)
        self.preferences = preferences
        config.db.store.add(self)

    def __repr__(self):
        short_user_id = self.user_id.int
        return '<User "{0.display_name}" ({2}) at {1:#x}>'.format(
            self, id(self), short_user_id)

    @property
    def user_id(self):
        """See `IUser`."""
        return self._user_id

    @property
    def created_on(self):
        """See `IUser`."""
        return self._created_on

    def link(self, address):
        """See `IUser`."""
        if address.user is not None:
            raise AddressAlreadyLinkedError(address)
        address.user = self

    def unlink(self, address):
        """See `IUser`."""
        if address.user is None:
            raise AddressNotLinkedError(address)
        address.user = None

    @property
    def preferred_address(self):
        """See `IUser`."""
        return self._preferred_address

    @preferred_address.setter
    def preferred_address(self, address):
        """See `IUser`."""
        if address.verified_on is None:
            raise UnverifiedAddressError(address)
        if self.controls(address.email):
            # This user already controls the email address.
            pass
        elif address.user is None:
            self.link(address)
        elif address.user != self:
            raise AddressAlreadyLinkedError(address)
        self._preferred_address = address

    @preferred_address.deleter
    def preferred_address(self):
        """See `IUser`."""
        self._preferred_address = None

    def controls(self, email):
        """See `IUser`."""
        found = config.db.store.find(Address, email=email)
        if found.count() == 0:
            return False
        assert found.count() == 1, 'Unexpected count'
        return found[0].user is self

    def register(self, email, display_name=None):
        """See `IUser`."""
        # First, see if the address already exists
        address = config.db.store.find(Address, email=email).one()
        if address is None:
            if display_name is None:
                display_name = ''
            address = Address(email=email, display_name=display_name)
            address.preferences = Preferences()
        # Link the address to the user if it is not already linked.
        if address.user is not None:
            raise AddressAlreadyLinkedError(address)
        address.user = self
        return address

    @property
    def memberships(self):
        return Memberships(self)
