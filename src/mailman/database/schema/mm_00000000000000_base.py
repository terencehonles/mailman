# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""Load the base schema."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'upgrade',
    'post_reset',
    'pre_reset',
    ]


_migration_path = None
VERSION = '00000000000000'



def upgrade(database, store, version, module_path):
    filename = '{0}.sql'.format(database.TAG)
    database.load_schema(store, version, filename, module_path)


def pre_reset(store):
    global _migration_path
    # Save the entry in the Version table for the test suite reset.  This will
    # be restored below.
    from mailman.model.version import Version
    result = store.find(Version, component=VERSION).one()
    # Yes, we abuse this field.
    _migration_path = result.version


def post_reset(store):
    from mailman.model.version import Version
    # We need to preserve the Version table entry for this migration, since
    # its existence defines the fact that the tables have been loaded.
    store.add(Version(component='schema', version=VERSION))
    store.add(Version(component=VERSION, version=_migration_path))
