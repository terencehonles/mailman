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
from mailman.model.member import Member
from mailman.model.preferences import Preferences
from mailman.model.user import User



class UserManager:
    implements(IUserManager)

    def create_user(self, email=None, display_name=None):
        """See `IUserManager`."""
        user = User(display_name, Preferences())
        if email:
            address = self.create_address(email, display_name)
            user.link(address)
        return user

    def delete_user(self, user):
        """See `IUserManager`."""
        config.db.store.remove(user)

    def get_user(self, email):
        """See `IUserManager`."""
        addresses = config.db.store.find(Address, email=email.lower())
        if addresses.count() == 0:
            return None
        return addresses.one().user

    def get_user_by_id(self, user_id):
        """See `IUserManager`."""
        users = config.db.store.find(User, _user_id=user_id)
        if users.count() == 0:
            return None
        return users.one()

    @property
    def users(self):
        """See `IUserManager`."""
        for user in config.db.store.find(User):
            yield user

    def create_address(self, email, display_name=None):
        """See `IUserManager`."""
        addresses = config.db.store.find(Address, email=email.lower())
        if addresses.count() == 1:
            found = addresses[0]
            raise ExistingAddressError(found.original_email)
        assert addresses.count() == 0, 'Unexpected results'
        if display_name is None:
            display_name = ''
        # It's okay not to lower case the 'email' argument because the
        # constructor will do the right thing.
        address = Address(email, display_name)
        address.preferences = Preferences()
        config.db.store.add(address)
        return address

    def delete_address(self, address):
        """See `IUserManager`."""
        # If there's a user controlling this address, it has to first be
        # unlinked before the address can be deleted.
        if address.user:
            address.user.unlink(address)
        config.db.store.remove(address)

    def get_address(self, email):
        """See `IUserManager`."""
        addresses = config.db.store.find(Address, email=email.lower())
        if addresses.count() == 0:
            return None
        return addresses.one()

    @property
    def addresses(self):
        """See `IUserManager`."""
        for address in config.db.store.find(Address):
            yield address

    @property
    def members(self):
        """See `IUserManager."""
        for member in config.db.store.find(Member):
                yield member
