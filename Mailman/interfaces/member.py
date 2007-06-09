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
        """The set of preferences for this subscription.

        This will return an IPreferences object using the following lookup
        rules:

        1. member
        2. address
        3. user
        4. mailing list
        5. system default
        """)

    role = Attribute(
        """The role of this membership.""")
