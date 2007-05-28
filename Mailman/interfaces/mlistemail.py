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

"""Interface for the email addresses associated with a mailing list."""

from zope.interface import Interface, Attribute



class IMailingListAddresses(Interface):
    """The email addresses associated with a mailing list.

    All attributes are read-only.
    """

    posting_address = Attribute(
        """The address to which messages are posted for copying to the full
        list membership, where 'full' of course means those members for which
        delivery is currently enabled.""")

    noreply_address = Attribute(
        """The address to which all messages will be immediately discarded,
        without prejudice or record.  This address is specific to the ddomain,
        even though it's available on the IMailingListAddresses interface.
        Generally, humans should never respond directly to this address.""")

    owner_address = Attribute(
        """The address which reaches the owners and moderators of the mailing
        list.  There is no address which reaches just the owners or just the
        moderators of a mailing list.""")

    request_address = Attribute(
        """The address which reaches the email robot for this mailing list.
        This robot can process various email commands such as changing
        delivery options, getting information or help about the mailing list,
        or processing subscrptions and unsubscriptions (although for the
        latter two, it's better to use the join_address and leave_address.""")

    bounces_address = Attribute(
        """The address which reaches the automated bounce processor for this
        mailing list.  Generally, humans should never respond directly to this
        address.""")

    join_address = Attribute(
        """The address to which subscription requests should be sent.  See
        subscribe_address for a backward compatible alias.""")

    leave_address = Attribute(
        """The address to which unsubscription requests should be sent.  See
        unsubscribe_address for a backward compatible alias.""")

    subscribe_address = Attribute(
        """Deprecated address to which subscription requests may be sent.
        This address is provided for backward compatibility only.  See
        join_address for the preferred alias.""")

    leave_address = Attribute(
        """Deprecated address to which unsubscription requests may be sent.
        This address is provided for backward compatibility only.  See
        leave_address for the preferred alias.""")

    def confirm_address(cookie=''):
        """The address used for various forms of email confirmation."""

