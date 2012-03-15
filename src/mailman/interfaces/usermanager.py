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

"""Interface describing the user management service."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IUserManager',
    ]


from zope.interface import Interface, Attribute



class IUserManager(Interface):
    """The global user management service."""

    def create_user(email=None, display_name=None):
        """Create and return an `IUser`.

        :param email: The text email address for the user being created.
        :type email: str
        :param display_name: The display name of the user.
        :type display_name: str
        :return: The newly created user, with the given email address and real
            name, if given.
        :rtype: `IUser`
        :raises ExistingAddressError: when the email address is already
            registered.
        """

    def delete_user(user):
        """Delete the given user.

        :param user: The user to delete.
        :type user: `IUser`.
        """

    def get_user(email):
        """Get the user that controls the given email address, or None.

        :param email: The email address to look up.
        :type email: str
        :return: The user found or None.
        :rtype: `IUser`.
        """

    def get_user_by_id(user_id):
        """Get the user associated with the given id.

        :param user_id: The user id.
        :type user_id: `uuid.UUID`
        :return: The user found or None.
        :rtype: `IUser`.
        """

    users = Attribute(
        """An iterator over all the `IUsers` managed by this user manager.""")

    def create_address(email, display_name=None):
        """Create and return an address unlinked to any user.

        :param email: The text email address for the address being created.
        :type email: str
        :param display_name: The display name associated with the address.
        :type display_name: str
        :return: The newly created address object, with the given email
            address and display name, if given.
        :rtype: `IAddress`
        :raises ExistingAddressError: when the email address is already
            registered.
        """

    def delete_address(address):
        """Delete the given `IAddress` object.

        If the `IAddress` is linked to a user, it is first unlinked before it
        is deleted.

        :param address: The address to delete.
        :type address: `IAddress`.
        """

    def get_address(email):
        """Find and return the `IAddress` matching an email address.

        :param email: The text email address.
        :type email: str
        :return: The matching `IAddress` object, or None if no registered
            `IAddress` matches the text address.
        :rtype: `IAddress` or None
        """

    addresses = Attribute(
        """An iterator over all the `IAddresses` managed by this manager.""")

    members = Attribute(
        """An iterator of all the `IMembers` in the database.""")
