# Copyright (C) 2006-2007 by the Free Software Foundation, Inc.
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

from __future__ import with_statement

import os

from elixir import objectstore

from Mailman.database.listmanager import ListManager
from Mailman.database.usermanager import UserManager

__all__ = [
    'initialize',
    'flush',
    ]



def initialize():
    from Mailman.LockFile import LockFile
    from Mailman.configuration import config
    from Mailman.database import model
    # Serialize this so we don't get multiple processes trying to create the
    # database at the same time.
    lockfile = os.path.join(config.LOCK_DIR, '<dbcreatelock>')
    with LockFile(lockfile):
        model.initialize()
    config.list_manager = ListManager()
    config.user_manager = UserManager()
    flush()


def flush():
    objectstore.flush()
