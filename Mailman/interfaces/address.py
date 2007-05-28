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

"""Interface for email address related information."""

from zope.interface import Interface, Attribute



class IAddress(Interface):
    """Email address related information."""

    address = Attribute(
        """Read-only text email address.""")

    real_name = Attribute(
        """Optional real name associated with the email address.""")

    registered_on = Attribute(
        """The date and time at which this email address was registered.

        Registeration is really the date at which this address became known to
        us.  It may have been explicitly registered by a user, or it may have
        been implicitly registered, e.g. by showing up in a non-member
        posting.""")

    validated_on = Attribute(
        """The date and time at which this email address was validated, or
        None if the email address has not yet been validated.  The specific
        method of validation is not defined here.""")
