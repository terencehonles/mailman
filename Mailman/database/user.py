# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

from email.utils import formataddr
from storm.locals import *
from zope.interface import implements

from Mailman.configuration import config
from Mailman.database.model import Model
from Mailman.database.address import Address
from Mailman.database.preferences import Preferences
from Mailman.interfaces import (
    AddressAlreadyLinkedError, AddressNotLinkedError, IUser)



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
        return '<User "%s" at %#x>' % (self.real_name, id(self))

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
                real_name = u''
            addrobj = Address(address=address, real_name=real_name)
            addrobj.preferences = Preferences()
        # Link the address to the user if it is not already linked.
        if addrobj.user is not None:
            raise AddressAlreadyLinkedError(addrobj)
        addrobj.user = self
        return addrobj
