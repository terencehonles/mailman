# Copyright (C) 2007-2011 by the Free Software Foundation, Inc.
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

"""Interface describing the basics of a user."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IUser',
    'UnverifiedAddressError',
    ]


from zope.interface import Interface, Attribute

from mailman.interfaces.errors import MailmanError



class UnverifiedAddressError(MailmanError):
    """Unverified address cannot be used as a user's preferred address."""

    def __init__(self, address):
        super(UnverifiedAddressError, self).__init__()
        self.address = address

    def __str__(self):
        return self.address



class IUser(Interface):
    """A basic user."""

    real_name = Attribute(
        """This user's real name.""")

    password = Attribute(
        """This user's password information.""")

    user_id = Attribute(
        """The user's unique, random identifier as a UUID.""")

    created_on = Attribute(
        """The date and time at which this user was created.""")

    addresses = Attribute(
        """An iterator over all the `IAddresses` controlled by this user.""")

    preferred_address = Attribute(
        """The user's preferred `IAddress`.  This must be validated.""")

    memberships = Attribute(
        """A roster of this user's memberships.""")

    def register(email, real_name=None):
        """Register the given email address and link it to this user.

        :param email: The text email address to register.
        :type email: str
        :param real_name: The user's real name.  If not given the empty string
            is used.
        :type real_name: str
        :return: The address object linked to the user.  If the associated
            address object already existed (unlinked to a user) then the
            `real_name` parameter is ignored.
        :rtype: `IAddress`
        :raises AddressAlreadyLinkedError: if this `IAddress` is already
            linked to another user.
        """

    def link(address):
        """Link this user to the given IAddress.

        Raises AddressAlreadyLinkedError if this IAddress is already linked to
        another user.
        """

    def unlink(address):
        """Unlink this IAddress from the user.

        Raises AddressNotLinkedError if this address is not linked to this
        user, either because it's not linked to any user or it's linked to
        some other user.
        """

    def controls(email):
        """Determine whether this user controls the given email address.

        :param email: The text email address to register.
        :type email: str
        :return: True if the user controls the given email address.
        :rtype: bool
        """

    preferences = Attribute(
        """This user's preferences.""")
