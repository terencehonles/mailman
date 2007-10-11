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

"""SQLAlchemy/Elixir based provider of IUserManager."""

from __future__ import with_statement

import os

from elixir import *
from zope.interface import implements

from Mailman import Errors
from Mailman.configuration import config
from Mailman.database.model import *
from Mailman.interfaces import IUserManager



class UserManager(object):
    implements(IUserManager)

    def create_user(self, address=None, real_name=None):
        user = User()
        user.real_name = (real_name if real_name is not None else '')
        if address:
            addrobj = Address(address, user.real_name)
            addrobj.preferences = Preferences()
            user.link(addrobj)
        user.preferences = Preferences()
        return user

    def delete_user(self, user):
        user.delete()

    @property
    def users(self):
        for user in User.select():
            yield user

    def get_user(self, address):
        found = Address.get_by(address=address.lower())
        return found and found.user

    def create_address(self, address, real_name=None):
        found = Address.get_by(address=address.lower())
        if found:
            raise Errors.ExistingAddressError(found.original_address)
        if real_name is None:
            real_name = ''
        address = Address(address, real_name)
        address.preferences = Preferences()
        return address

    def delete_address(self, address):
        # If there's a user controlling this address, it has to first be
        # unlinked before the address can be deleted.
        if address.user:
            address.user.unlink(address)
        address.delete()

    def get_address(self, address):
        return Address.get_by(address=address.lower())

    @property
    def addresses(self):
        for address in Address.select():
            yield address
