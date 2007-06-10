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
from Mailman.interfaces import IUser

ADDRESS_KIND    = 'Mailman.database.model.address.Address'
PREFERENCE_KIND = 'Mailman.database.model.profile.Preferences'



class User(Entity):
    implements(IUser)

    has_field('real_name',  Unicode)
    has_field('password',   Unicode)
    # Relationships
    has_many('addresses',       of_kind=ADDRESS_KIND)
    belongs_to('preferences',   of_kind=PREFERENCE_KIND)
    # Options
    using_options(shortnames=True)

    def __repr__(self):
        return '<User "%s" at %#x>' % (self.real_name, id(self))

    def link(self, address):
        if address.user is not None:
            raise Errors.AddressAlreadyLinkedError(address)
        address.user = self
        self.addresses.append(address)

    def unlink(self, address):
        if address.user is None:
            raise Errors.AddressNotLinkedError(address)
        address.user = None
        self.addresses.remove(address)

    def controls(self, address):
        found = Address.get_by(address=address)
        return bool(found and found.user is self)
