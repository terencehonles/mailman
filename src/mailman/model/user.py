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

"""Model for users."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'User',
    ]

from storm.locals import *
from zope.interface import implements

from mailman.config import config
from mailman.database.model import Model
from mailman.interfaces.address import (
    AddressAlreadyLinkedError, AddressNotLinkedError)
from mailman.interfaces.user import IUser
from mailman.model.address import Address
from mailman.model.preferences import Preferences
from mailman.model.roster import Memberships



class User(Model):
    """Mailman users."""

    implements(IUser)

    id = Int(primary=True)
    real_name = Unicode()
    password = Unicode()

    addresses = ReferenceSet(id, 'Address.user_id')
    preferences_id = Int()
    preferences = Reference(preferences_id, 'Preferences.id')

    def __repr__(self):
        return '<User "{0}" at {1:#x}>'.format(self.real_name, id(self))

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

    def controls(self, address):
        """See `IUser`."""
        found = config.db.store.find(Address, address=address)
        if found.count() == 0:
            return False
        assert found.count() == 1, 'Unexpected count'
        return found[0].user is self

    def register(self, address, real_name=None):
        """See `IUser`."""
        # First, see if the address already exists
        addrobj = config.db.store.find(Address, address=address).one()
        if addrobj is None:
            if real_name is None:
                real_name = ''
            addrobj = Address(address=address, real_name=real_name)
            addrobj.preferences = Preferences()
        # Link the address to the user if it is not already linked.
        if addrobj.user is not None:
            raise AddressAlreadyLinkedError(addrobj)
        addrobj.user = self
        return addrobj

    @property
    def memberships(self):
        return Memberships(self)
