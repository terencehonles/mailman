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

"""Interface for a roster of members."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IRoster',
    ]


from zope.interface import Interface, Attribute



class IRoster(Interface):
    """A roster is a collection of `IMembers`."""

    name = Attribute(
        """The name for this roster.

        Rosters are considered equal if they have the same name.""")

    members = Attribute(
        """An iterator over all the IMembers managed by this roster.""")

    member_count = Attribute(
        """The number of members managed by this roster.""")

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
        """Get the member for the given address.

        :param address: The email address to search for.
        :type address: text
        :return: The member if found, otherwise None
        :rtype: `IMember` or None
        """
