# Copyright (C) 2006 by the Free Software Foundation, Inc.
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

# This module exposes the higher level interface methods that the rest of
# Mailman should use.  It essentially hides the dbcontext and the SQLAlchemy
# session from all other code.  The preferred way to use these methods is:
#
# from Mailman import database
# database.add_list(foo)


def initialize():
    from Mailman import database
    from Mailman.database.dbcontext import dbcontext

    dbcontext.connect()
    for attr in dir(dbcontext):
        if attr.startswith('api_'):
            exposed_name = attr[4:]
            setattr(database, exposed_name, getattr(dbcontext, attr))
