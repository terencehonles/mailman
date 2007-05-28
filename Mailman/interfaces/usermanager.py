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

"""Interface describing a user manager service."""

from zope.interface import Interface, Attribute



class IUserManager(Interface):
    """The interface of a global user manager service.

    Different user managers have different concepts of what a user is, and the
    users managed by different IUserManagers are completely independent.  This
    is how you can separate the user contexts for different domains, on a
    multiple domain system.

    There is one special roster, the null roster ('') which contains all
    IUsers in all IRosters.
    """

    def create_roster(name):
        """Create and return the named IRoster.

        Raises RosterExistsError if the named roster already exists.
        """

    def get_roster(name):
        """Return the named IRoster.

        Raises NoSuchRosterError if the named roster doesnot yet exist.
        """

    def delete_roster(name):
        """Delete the named IRoster.

        Raises NoSuchRosterError if the named roster doesnot yet exist.
        """

    rosters = Attribute(
        """An iterator over all IRosters managed by this user manager.""")

    def create_user():
        """Create and return an IUser."""

    def delete_user(user):
        """Delete the given IUser."""

    def get_user(address):
        """Get the user that controls the given email address, or None.

        'address' is a text email address.
        """

    users = Attribute(
        """An iterator over all the IUsers managed by this user manager.""")

    def create_rosterset():
        """Create and return a new IRosterSet.

        IRosterSets manage groups of IRosters.
        """

    def delete_rosterset(rosterset):
        """Delete the given IRosterSet."""

    def get_rosterset(serial):
        """Return the IRosterSet that matches the serial number, or None."""
