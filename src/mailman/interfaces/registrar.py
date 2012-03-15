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

"""Interface describing a user registration service.

This is a higher level interface to user registration, address confirmation,
etc. than the IUserManager.  The latter does no validation, syntax checking,
or confirmation, while this interface does.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IRegistrar',
    ]


from zope.interface import Interface



class IRegistrar(Interface):
    """Interface for registering and verifying email addresses and users.

    This is a higher level interface to user registration, email address
    confirmation, etc. than the IUserManager.  The latter does no validation,
    syntax checking, or confirmation, while this interface does.
    """

    def register(mlist, email, display_name=None, delivery_mode=None):
        """Register the email address, requesting verification.

        No `IAddress` or `IUser` is created during this step, but after
        successful confirmation, it is guaranteed that an `IAddress` with a
        linked `IUser` will exist.  When a verified `IAddress` matching
        `email` already exists, this method will do nothing, except link a new
        `IUser` to the `IAddress` if one is not yet associated with the
        email address.

        In all cases, the email address is sanity checked for validity first.

        :param mlist: The mailing list that is the focus of this registration.
        :type mlist: `IMailingList`
        :param email: The email address to register.
        :type email: str
        :param display_name: The optional display name of the user.
        :type display_name: str
        :param delivery_mode: The optional delivery mode for this
            registration.  If not given, regular delivery is used.
        :type delivery_mode: `DeliveryMode`
        :return: The confirmation token string.
        :rtype: str
        :raises InvalidEmailAddressError: if the address is not allowed.
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
