# Copyright (C) 2007-2011 by the Free Software Foundation, Inc.
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
from zope.interface import implements

from mailman.config import config
from mailman.database.model import Model
from mailman.interfaces.address import (
    AddressAlreadyLinkedError, AddressNotLinkedError)
from mailman.interfaces.user import IUser
from mailman.model.address import Address
from mailman.model.preferences import Preferences
from mailman.model.roster import Memberships
from mailman.utilities.datetime import factory as date_factory
from mailman.utilities.uid import factory as uid_factory



class User(Model):
    """Mailman users."""

    implements(IUser)

    id = Int(primary=True)
    real_name = Unicode()
    password = RawStr()
    _user_id = Unicode()
    _created_on = DateTime()

    addresses = ReferenceSet(id, 'Address.user_id')
    preferences_id = Int()
    preferences = Reference(preferences_id, 'Preferences.id')

    def __init__(self, real_name=None, preferences=None):
        super(User, self).__init__()
        self._created_on = date_factory.now()
        self._user_id = uid_factory.new_uid()
        self.real_name = ('' if real_name is None else real_name)
        self.preferences = preferences
        config.db.store.add(self)

    def __repr__(self):
        return '<User "{0.real_name}" ({0.user_id}) at {1:#x}>'.format(
            self, id(self))

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

    def controls(self, email):
        """See `IUser`."""
        found = config.db.store.find(Address, email=email)
        if found.count() == 0:
            return False
        assert found.count() == 1, 'Unexpected count'
        return found[0].user is self

    def register(self, email, real_name=None):
        """See `IUser`."""
        # First, see if the address already exists
        address = config.db.store.find(Address, email=email).one()
        if address is None:
            if real_name is None:
                real_name = ''
            address = Address(email=email, real_name=real_name)
            address.preferences = Preferences()
        # Link the address to the user if it is not already linked.
        if address.user is not None:
            raise AddressAlreadyLinkedError(address)
        address.user = self
        return address

    @property
    def memberships(self):
        return Memberships(self)
