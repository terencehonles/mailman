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

"""Interface describing the basics of a user."""

from zope.interface import Interface, Attribute



class IUser(Interface):
    """A basic user."""

    real_name = Attribute(
        """This user's Real Name.""")

    password = Attribute(
        """This user's password information.""")

    profile = Attribute(
        """The default IProfile for this user.""")

    addresses = Attribute(
        """An iterator over all the IAddresses controlled by this user.""")

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
