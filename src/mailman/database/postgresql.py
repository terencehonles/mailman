# Copyright (C) 2011 by the Free Software Foundation, Inc.
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

"""PostgreSQL database support."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'PostgreSQLDatabase',
    ]


from pkg_resources import resource_string

from mailman.database.base import StormBaseDatabase



class PostgreSQLDatabase(StormBaseDatabase):
    """Database class for PostgreSQL."""

    def _database_exists(self, store):
        """See `BaseDatabase`."""
        table_query = ('SELECT table_name FROM information_schema.tables '
                       "WHERE table_schema = 'public'")
        table_names = set(item[0] for item in 
                          store.execute(table_query))
        return 'version' in table_names

    def _get_schema(self):
        """See `BaseDatabase`."""
        return resource_string('mailman.database.sql', 'postgres.sql')
