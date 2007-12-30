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


"""Interface describing the basics of a member."""

from munepy import Enum
from zope.interface import Interface, Attribute

__all__ = [
    'DeliveryMode',
    'DeliveryStatus',
    'IMember',
    'MemberRole',
    ]



class DeliveryMode(Enum):
    # Regular (i.e. non-digest) delivery
    regular = 1
    # Plain text digest delivery
    plaintext_digests = 2
    # MIME digest delivery
    mime_digests = 3
    # Summary digests
    summary_digests = 4



class DeliveryStatus(Enum):
    # Delivery is enabled
    enabled = 1
    # Delivery was disabled by the user
    by_user = 2
    # Delivery was disabled due to bouncing addresses
    by_bounces = 3
    # Delivery was disabled by an administrator or moderator
    by_moderator = 4
    # Disabled for unknown reasons.
    unknown = 5



class MemberRole(Enum):
    member = 1
    owner = 2
    moderator = 3



class IMember(Interface):
    """A member of a mailing list."""

    mailing_list = Attribute(
        """The mailing list subscribed to.""")

    address = Attribute(
        """The email address that's subscribed to the list.""")

    preferences = Attribute(
        """This member's preferences.""")

    role = Attribute(
        """The role of this membership.""")

    is_moderated = Attribute(
        """True if the membership is moderated, otherwise False.""")

    def unsubscribe():
        """Unsubscribe (and delete) this member from the mailing list."""

    acknowledge_posts = Attribute(
        """Send an acknowledgment for every posting?

        Unlike going through the preferences, this attribute return the
        preference value based on the following lookup order:

        1. The member
        2. The address
        3. The user
        4. System default
        """)

    preferred_language = Attribute(
        """The preferred language for interacting with a mailing list.

        Unlike going through the preferences, this attribute return the
        preference value based on the following lookup order:

        1. The member
        2. The address
        3. The user
        4. System default
        """)

    receive_list_copy = Attribute(
        """Should an explicit recipient receive a list copy?

        Unlike going through the preferences, this attribute return the
        preference value based on the following lookup order:

        1. The member
        2. The address
        3. The user
        4. System default
        """)

    receive_own_postings = Attribute(
        """Should the poster get a list copy of their own messages?

        Unlike going through the preferences, this attribute return the
        preference value based on the following lookup order:

        1. The member
        2. The address
        3. The user
        4. System default
        """)

    delivery_mode = Attribute(
        """The preferred delivery mode.

        Unlike going through the preferences, this attribute return the
        preference value based on the following lookup order:

        1. The member
        2. The address
        3. The user
        4. System default
        """)

    delivery_status = Attribute(
        """The delivery status.

        Unlike going through the preferences, this attribute return the
        preference value based on the following lookup order:

        1. The member
        2. The address
        3. The user
        4. System default

        XXX I'm not sure this is the right place to put this.""")

    options_url = Attribute(
        """Return the url for the given member's option page.

        XXX This needs a serious re-think in the face of the unified user
        database, since a member's options aren't tied to any specific mailing
        list.  So in what part of the web-space does the user's options live?
        """)
