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

"""Interface for a profile, which describes delivery related information."""

from zope.interface import Interface, Attribute



class IProfile(Interface):
    """Delivery related information."""

    acknowledge_posts = Attribute(
        """Boolean specifying whether to send an acknowledgment receipt for
        every posting to the mailing list.
        """)

    hide_address = Attribute(
        """Boolean specifying whether to hide this email address from fellow
        list members.
        """)

    preferred_language = Attribute(
        """Preferred language for interacting with a mailing list.""")

    receive_list_copy = Attribute(
        """Boolean specifying whether to receive a list copy if the user is
        explicitly named in one of the recipient headers.
        """)

    receive_own_postings = Attribute(
        """Boolean specifying whether to receive a list copy of the user's own
        postings to the mailing list.
        """)

    delivery_mode = Attribute(
        """The preferred delivery mode.

        This is an enum constant of the type DeliveryMode.""")
