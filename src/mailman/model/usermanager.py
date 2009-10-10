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

"""A user manager."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'UserManager',
    ]


from zope.interface import implements

from mailman.config import config
from mailman.interfaces.address import ExistingAddressError
from mailman.interfaces.usermanager import IUserManager
from mailman.model.address import Address
from mailman.model.preferences import Preferences
from mailman.model.user import User



class UserManager:
    implements(IUserManager)

    def create_user(self, address=None, real_name=None):
        user = User()
        user.real_name = ('' if real_name is None else real_name)
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
        for user in config.db.store.find(User):
            yield user

    def get_user(self, address):
        addresses = config.db.store.find(Address, address=address.lower())
        if addresses.count() == 0:
            return None
        elif addresses.count() == 1:
            return addresses[0].user
        else:
            raise AssertionError('Unexpected query count')

    def create_address(self, address, real_name=None):
        addresses = config.db.store.find(Address, address=address.lower())
        if addresses.count() == 1:
            found = addresses[0]
            raise ExistingAddressError(found.original_address)
        assert addresses.count() == 0, 'Unexpected results'
        if real_name is None:
            real_name = ''
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
        addresses = config.db.store.find(Address, address=address.lower())
        if addresses.count() == 0:
            return None
        elif addresses.count() == 1:
            return addresses[0]
        else:
            raise AssertionError('Unexpected query count')

    @property
    def addresses(self):
        for address in config.db.store.find(Address):
            yield address
