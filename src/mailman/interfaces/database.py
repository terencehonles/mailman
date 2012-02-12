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

"""Interfaces for database interaction."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'DatabaseError',
    'IDatabase',
    ]


from zope.interface import Interface

from mailman.interfaces.errors import MailmanError



class DatabaseError(MailmanError):
    """A problem with the database occurred."""



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
