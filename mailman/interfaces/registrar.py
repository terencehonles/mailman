# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""Interface describing a user registration service.

This is a higher level interface to user registration, address confirmation,
etc. than the IUserManager.  The latter does no validation, syntax checking,
or confirmation, while this interface does.
"""

from zope.interface import Interface, Attribute



class IRegistrar(Interface):
    """Interface for registering and verifying addresses and users.

    This is a higher level interface to user registration, address
    confirmation, etc. than the IUserManager.  The latter does no validation,
    syntax checking, or confirmation, while this interface does.
    """

    def register(address, real_name=None, mlist=None):
        """Register the email address, requesting verification.

        No IAddress or IUser is created during this step, but after successful
        confirmation, it is guaranteed that an IAddress with a linked IUser
        will exist.  When a verified IAddress matching address already exists,
        this method will do nothing, except link a new IUser to the IAddress
        if one is not yet associated with the address.

        In all cases, the email address is sanity checked for validity first.

        :param address: The textual email address to register.
        :param real_name: The optional real name of the user.
        :return: The confirmation token string.
        :raises InvalidEmailAddress: if the address is not allowed.
        """

    def confirm(token):
        """Confirm the pending registration matched to the given `token`.

        Confirmation ensures that the IAddress exists and is linked to an
        IUser, with the latter being created and linked if necessary.

        :param token: A token matching a pending event with a type of
            'registration'.
        :return: Boolean indicating whether the confirmation succeeded or
            not.  It may fail if the token is no longer in the database, or if
            the token did not match a registration event.
        """

    def discard(token):
        """Discard the pending registration matched to the given `token`.

        The event record is discarded and the IAddress is not verified.  No
        IUser is created.

        :param token: A token matching a pending event with a type of
            'registration'.
        """
