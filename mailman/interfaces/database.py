# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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

"""Interfaces for database interaction.

By providing an object with this interface and declaring it in a package
setup.py file as an entry point in the 'mailman.database' group with the name
'initializer', you can distribute entirely different database layers for
Mailman's back end.
"""

__metaclass__ = type
__all__ = [
    'DatabaseError',
    'IDatabase',
    'SchemaVersionMismatchError',
    ]

from zope.interface import Interface, Attribute

from mailman.interfaces.errors import MailmanError
from mailman.version import DATABASE_SCHEMA_VERSION



class DatabaseError(MailmanError):
    """A problem with the database occurred."""


class SchemaVersionMismatchError(DatabaseError):
    """The database schema version number did not match what was expected."""

    def __init__(self, got):
        super(SchemaVersionMismatchError, self).__init__()
        self._got = got

    def __str__(self):
        return (
            'Incompatible database schema version (got: %d, expected: %d)'
            % (self._got, DATABASE_SCHEMA_VERSION))



class IDatabase(Interface):
    """Database layer interface."""

    def initialize(debug=None):
        """Initialize the database layer, using whatever means necessary.

        :param debug: When None (the default), the configuration file
            determines whether the database layer should have increased
            debugging or not.  When True or False, this overrides the
            configuration file setting.
        """

    def _reset():
        """Reset the database to its pristine state.

        This is only used by the test framework.
        """

    def begin():
        """Begin the current transaction."""

    def commit():
        """Commit the current transaction."""

    def abort():
        """Abort the current transaction."""

    list_manager = Attribute(
        """The IListManager instance provided by the database layer.""")

    user_manager = Attribute(
        """The IUserManager instance provided by the database layer.""")

    message_store = Attribute(
        """The IMessageStore instance provided by the database layer.""")

    pendings = Attribute(
        """The IPending instance provided by the database layer.""")
