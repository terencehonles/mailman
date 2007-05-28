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
    """A roster is a collection of IUsers."""

    name = Attribute(
        """The name for this roster.

        Rosters are considered equal if they have the same name.""")

    addresses = Attribute(
        """An iterator over all the addresses managed by this roster.""")

    def create(email_address, real_name=None):
        """Create an IAddress and return it.

        email_address is textual email address to add.  real_name is the
        optional real name that gets associated with the email address.

        Raises ExistingAddressError if address already exists.
        """
