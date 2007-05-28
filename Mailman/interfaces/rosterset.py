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

"""Interface for a collection of rosters."""

from zope.interface import Interface, Attribute



class IRosterSet(Interface):
    """A collection of IRosters."""

    serial = Attribute(
        """The unique integer serial number for this roster set.

        This is necessary to enforce the separation between the list storage
        and the user/roster storage.  You should always reference a roster set
        indirectly through its serial number.""")

    rosters = Attribute(
        """An iterator over all the IRosters in this collection.""")

    def add(roster):
        """Add the IRoster to this collection.

        Does nothing if the roster is already a member of this collection.
        """

    def delete(roster):
        """Delete the IRoster from this collection.

        Does nothing if the roster is not a member of this collection.
        """
