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

from zope.interface import Interface, Attribute



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

    def unsubscribe():
        """Unsubscribe (and delete) this member from the mailing list."""

    acknowledge_posts = Attribute(
        """This is the actual acknowledgment setting for this member.

        Unlike going through the preferences, this attribute return the
        preference value based on the following lookup order:

        1. The member
        2. The address
        3. The user
        4. System default
        """)

    delivery_mode = Attribute(
        """This is the actual delivery mode for this member.

        Unlike going through the preferences, this attribute return the
        preference value based on the following lookup order:

        1. The member
        2. The address
        3. The user
        4. System default
        """)

    preferred_language = Attribute(
        """This is the actual preferred language for this member.

        Unlike going through the preferences, this attribute return the
        preference value based on the following lookup order:

        1. The member
        2. The address
        3. The user
        4. System default
        """)

    options_url = Attribute(
        """Return the url for the given member's option page.

        XXX This needs a serious re-think in the face of the unified user
        database, since a member's options aren't tied to any specific mailing
        list.  So in what part of the web-space does the user's options live?
        """)
