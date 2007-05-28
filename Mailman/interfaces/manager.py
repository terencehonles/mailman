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

"""Generic database object manager interface."""

from zope.interface import Interface, Attribute



class IManaged(Interface):
    """An object managed by an IManager."""

    name = Attribute("""The name of the managed object.""")



class IManager(Interface):
    """Create and manage profiles."""

    def create(name):
        """Create and return a new IManaged object.

        name is the unique name for this object.  Raises
        ExistingManagedObjectError if an IManaged object with the given name
        already exists.
        """

    def get(name):
        """Return the named IManaged object.

        Raises NoSuchManagedObjectError if the named IManaged object does not
        exist.
        """

    def delete(name):
        """Delete the named IManaged object.

        Raises NoSuchManagedObjectError if the named IManaged object does not
        exist.
        """

    iterator = Attribute(
        """Return an iterator over the all the IManaged objects.""")
