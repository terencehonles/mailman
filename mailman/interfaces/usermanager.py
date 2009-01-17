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

"""Interface describing a user manager service."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IUserManager',
    ]


from zope.interface import Interface, Attribute



class IUserManager(Interface):
    """The interface of a global user manager service.

    Different user managers have different concepts of what a user is, and the
    users managed by different IUserManagers are completely independent.  This
    is how you can separate the user contexts for different domains, on a
    multiple domain system.

    There is one special roster, the null roster ('') which contains all
    IUsers in all IRosters.
    """

    def create_user(address=None, real_name=None):
        """Create and return an IUser.

        When address is given, an IAddress is also created and linked to the
        new IUser object.  If the address already exists, an
        `ExistingAddressError` is raised.  If the address exists but is
        already linked to another user, an AddressAlreadyLinkedError is
        raised.

        When real_name is given, the IUser's real_name is set to this string.
        If an IAddress is also created and linked, its real_name is set to the
        same string.
        """

    def delete_user(user):
        """Delete the given IUser."""

    def get_user(address):
        """Get the user that controls the given email address, or None.

        'address' is a text email address.
        """

    users = Attribute(
        """An iterator over all the IUsers managed by this user manager.""")

    def create_address(address, real_name=None):
        """Create and return an unlinked IAddress object.

        address is the text email address.  If real_name is not given, it
        defaults to the empty string.  If the IAddress already exists an
        ExistingAddressError is raised.
        """

    def delete_address(address):
        """Delete the given IAddress object.

        If this IAddress linked to a user, it is first unlinked before it is
        deleted.
        """

    def get_address(address):
        """Find and return the `IAddress` matching a text address.

        :param address: the text email address
        :type address: string
        :return: The matching `IAddress` object, or None if no registered
            `IAddress` matches the text address
        :rtype: `IAddress` or None
        """

    addresses = Attribute(
        """An iterator over all the IAddresses managed by this manager.""")
