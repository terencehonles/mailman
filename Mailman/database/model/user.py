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

from elixir import *
from email.utils import formataddr
from zope.interface import implements

from Mailman import Errors
from Mailman.database.model import Address
from Mailman.database.model import Preferences
from Mailman.interfaces import IUser

ADDRESS_KIND    = 'Mailman.database.model.address.Address'
PREFERENCE_KIND = 'Mailman.database.model.preferences.Preferences'



class User(Entity):
    implements(IUser)

    real_name = Field(Unicode)
    password = Field(Unicode)

    addresses = OneToMany(ADDRESS_KIND)
    preferences = ManyToOne(PREFERENCE_KIND)

    def __repr__(self):
        return '<User "%s" at %#x>' % (self.real_name, id(self))

    def link(self, address):
        if address.user is not None:
            raise Errors.AddressAlreadyLinkedError(address)
        address.user = self

    def unlink(self, address):
        if address.user is None:
            raise Errors.AddressNotLinkedError(address)
        address.user = None

    def controls(self, address):
        found = Address.get_by(address=address)
        return bool(found and found.user is self)

    def register(self, address, real_name=None):
        # First, see if the address already exists
        addrobj = Address.get_by(address=address)
        if addrobj is None:
            if real_name is None:
                real_name = ''
            addrobj = Address(address=address, real_name=real_name)
            addrobj.preferences = Preferences()
        # Link the address to the user if it is not already linked.
        if addrobj.user is not None:
            raise Errors.AddressAlreadyLinkedError(addrobj)
        addrobj.user = self
        return addrobj
