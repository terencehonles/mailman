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

"""Interface for a roster of members."""

from zope.interface import Interface, Attribute



class IRoster(Interface):
    """A roster is a collection of IMembers."""

    name = Attribute(
        """The name for this roster.

        Rosters are considered equal if they have the same name.""")

    members = Attribute(
        """An iterator over all the IMembers managed by this roster.""")

    users = Attribute(
        """An iterator over all the IUsers reachable by this roster.

        This returns all the users for all the members managed by this roster.
        """)

    addresses = Attribute(
        """An iterator over all the IAddresses reachable by this roster.

        This returns all the addresses for all the users for all the members
        managed by this roster.
        """)

    def get_member(address):
        """Return the IMember for the given address.

        'address' is a text email address.  If no matching member is found,
        None is returned.
        """
