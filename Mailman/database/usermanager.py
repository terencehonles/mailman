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

"""A user manager."""

from __future__ import with_statement

import os

from zope.interface import implements

from Mailman import Errors
from Mailman.configuration import config
from Mailman.interfaces import IUserManager



class UserManager(object):
    implements(IUserManager)

    def create_user(self, address=None, real_name=None):
        # Avoid circular imports.
        from Mailman.database.model import Address, Preferences, User
        user = User()
        user.real_name = (u'' if real_name is None else real_name)
        if address:
            addrobj = Address(address, user.real_name)
            addrobj.preferences = Preferences()
            user.link(addrobj)
        user.preferences = Preferences()
        config.db.store.add(user)
        return user

    def delete_user(self, user):
        config.db.store.remove(user)

    @property
    def users(self):
        # Avoid circular imports.
        from Mailman.database.model import User
        for user in config.db.store.find(User):
            yield user

    def get_user(self, address):
        # Avoid circular imports.
        from Mailman.database.model import Address
        addresses = config.db.store.find(Address, address=address.lower())
        if addresses.count() == 0:
            return None
        elif addresses.count() == 1:
            return addresses[0].user
        else:
            raise AssertionError('Unexpected query count')

    def create_address(self, address, real_name=None):
        # Avoid circular imports.
        from Mailman.database.model import Address, Preferences
        addresses = config.db.store.find(Address, address=address.lower())
        if addresses.count() == 1:
            found = addresses[0]
            raise Errors.ExistingAddressError(found.original_address)
        assert addresses.count() == 0, 'Unexpected results'
        if real_name is None:
            real_name = u''
        # It's okay not to lower case the 'address' argument because the
        # constructor will do the right thing.
        address = Address(address, real_name)
        address.preferences = Preferences()
        config.db.store.add(address)
        return address

    def delete_address(self, address):
        # If there's a user controlling this address, it has to first be
        # unlinked before the address can be deleted.
        if address.user:
            address.user.unlink(address)
        config.db.store.remove(address)

    def get_address(self, address):
        # Avoid circular imports.
        from Mailman.database.model import Address
        addresses = config.db.store.find(Address, address=address.lower())
        if addresses.count() == 0:
            return None
        elif addresses.count() == 1:
            return addresses[0]
        else:
            raise AssertionError('Unexpected query count')

    @property
    def addresses(self):
        # Avoid circular imports.
        from Mailman.database.model.address import Address
        for address in config.db.store.find(Address):
            yield address
