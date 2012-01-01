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

"""Interfaces for the pending database.

The pending database contains events that must be confirmed by the user.  It
maps these events to a unique hash that can be used as a token for end user
confirmation.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IPendable',
    'IPended',
    'IPendedKeyValue',
    'IPendings',
    ]


from zope.interface import Interface, Attribute



class IPendable(Interface):
    """A pendable object."""

    def keys():
        """The keys of the pending event data, all of which are strings."""

    def values():
        """The values of the pending event data, all of which are strings."""

    def items():
        """The key/value pairs of the pending event data.

        Both the keys and values must be strings.
        """



class IPended(Interface):
    """A pended event, tied to a token."""

    token = Attribute("""The pended token.""")

    expiration_date = Attribute("""The expiration date of the pended event.""")



class IPendedKeyValue(Interface):
    """A pended key/value pair."""

    key = Attribute("""The pended key.""")

    value = Attribute("""The pended value.""")



class IPendings(Interface):
    """Interface to pending database."""

    def add(pendable, lifetime=None):
        """Create a new entry in the pending database, returning a token.

        :param pendable: The IPendable instance to add.
        :param lifetime: The amount of time, as a `datetime.timedelta` that
            the pended item should remain in the database.  When None is
            given, a system default maximum lifetime is used.
        :return: A token string for inclusion in urls and email confirmations.
        """

    def confirm(token, expunge=True):
        """Return the IPendable matching the token.

        :param token: The token string for the IPendable given by the `.add()`
            method.
        :param expunge: A flag indicating whether the pendable record should
            also be removed from the database or not.
        :return: The matching IPendable or None if no match was found.
        """

    def evict():
        """Remove all pended items whose lifetime has expired."""
