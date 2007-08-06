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

"""Interface for email address related information."""

from zope.interface import Interface, Attribute



class IAddress(Interface):
    """Email address related information."""

    address = Attribute(
        """Read-only text email address.""")

    original_address = Attribute(
        """Read-only original case-preserved address.

        For almost all intents and purposes, addresses in Mailman are case
        insensitive, however because RFC 2821 allows for case sensitive local
        parts, Mailman preserves the case of the original address when
        emailing the user.

        `original_address` will be the same as address if the original address
        was all lower case.  Otherwise `original_address` will be the case
        preserved address; `address` will always be lower case.
        """)

    real_name = Attribute(
        """Optional real name associated with the email address.""")

    registered_on = Attribute(
        """The date and time at which this email address was registered.

        Registeration is really the date at which this address became known to
        us.  It may have been explicitly registered by a user, or it may have
        been implicitly registered, e.g. by showing up in a non-member
        posting.""")

    verified_on = Attribute(
        """The date and time at which this email address was validated, or
        None if the email address has not yet been validated.  The specific
        method of validation is not defined here.""")

    def subscribe(mailing_list, role):
        """Subscribe the address to the given mailing list with the given role.

        :param mailing_list: The IMailingList being subscribed to.
        :param role: A MemberRole enum value.
        :return: The IMember representing this subscription.
        :raises AlreadySubscribedError: If the address is already subscribed
            to the mailing list with the given role.
        """

    preferences = Attribute(
        """This address's preferences.""")
