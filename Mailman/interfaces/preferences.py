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

"""Interface for preferences."""

from zope.interface import Interface, Attribute



class IPreferences(Interface):
    """Delivery related information."""

    acknowledge_posts = Attribute(
        """Send an acknowledgment for every posting?

        This preference can be True, False, or None.  True means the user is
        sent a receipt for each message they send to the mailing list.  False
        means that no receipt is sent.  None means no preference is
        specified.""")

    preferred_language = Attribute(
        """The preferred language for interacting with a mailing list.

        This is either the language code for the preferred language, or None
        meaning no preferred language is specified.""")

    receive_list_copy = Attribute(
        """Should an explicit recipient receive a list copy?

        When a list member is explicitly named in a message's recipients
        (e.g. the To or CC headers), and this preference is True, the
        recipient will still receive a list copy of the message.  When False,
        this list copy will be suppressed.  None means no preference is
        specified.""")

    receive_own_postings = Attribute(
        """Should the poster get a list copy of their own messages?

        When this preference is True, a list copy will be sent to the poster
        of all messages.  When False, this list copy will be suppressed.  None
        means no preference is specified.""")

    delivery_mode = Attribute(
        """The preferred delivery mode.

        This is an enum constant of the type DeliveryMode.  It may also be
        None which means that no preference is specified.""")

    delivery_status = Attribute(
        """The delivery status.

        This is an enum constant of type DeliveryStatus.  It may also be None
        which means that no preference is specified.

        XXX I'm not sure this is the right place to put this.""")
