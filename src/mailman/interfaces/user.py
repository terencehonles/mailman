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

"""Interface describing the basics of a user."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IUser',
    ]


from zope.interface import Interface, Attribute



class IUser(Interface):
    """A basic user."""

    real_name = Attribute(
        """This user's Real Name.""")

    password = Attribute(
        """This user's password information.""")

    addresses = Attribute(
        """An iterator over all the IAddresses controlled by this user.""")

    memberships = Attribute(
        """A roster of this user's membership.""")

    def register(address, real_name=None):
        """Register the given email address and link it to this user.

        In this case, 'address' is a text email address, not an IAddress
        object.  If real_name is not given, the empty string is used.

        Raises AddressAlreadyLinkedError if this IAddress is already linked to
        another user.  If the corresponding IAddress already exists but is not
        linked, then it is simply linked to the user, in which case
        real_name is ignored.

        Return the new IAddress object.
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

    def controls(address):
        """Determine whether this user controls the given email address.

        'address' is a text email address.  This method returns true if the
        user controls the given email address, otherwise false.
        """

    preferences = Attribute(
        """This user's preferences.""")
