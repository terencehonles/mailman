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

"""SQLAlchemy/Elixir based provider of IUserManager."""

from __future__ import with_statement

import os

from elixir import *
from zope.interface import implements

from Mailman import Errors
from Mailman.LockFile import LockFile
from Mailman.configuration import config
from Mailman.database.model import *
from Mailman.interfaces import IUserManager



class UserManager(object):
    implements(IUserManager)

    def __init__(self):
        # Create the null roster if it does not already exist.  It's more
        # likely to exist than not so try to get it before creating it.
        lockfile = os.path.join(config.LOCK_DIR, '<umgrcreatelock>')
        with LockFile(lockfile):
            roster = self.get_roster('')
            if roster is None:
                self.create_roster('')
        objectstore.flush()

    def create_roster(self, name):
        roster = Roster.get_by(name=name)
        if roster:
            raise Errors.RosterExistsError(name)
        return Roster(name=name)

    def get_roster(self, name):
        return Roster.get_by(name=name)

    def delete_roster(self, roster):
        roster.delete()

    @property
    def rosters(self):
        for roster in Roster.select():
            yield roster

    def create_rosterset(self, name):
        return RosterSet(name=name)

    def delete_rosterset(self, rosterset):
        rosterset.delete()

    def get_rosterset(self, name):
        return RosterSet.get_by(name=name)

    def create_user(self):
        user = User()
        # Users always have a profile
        user.profile = Profile()
        user.profile.user = user
        return user

    def delete_user(self, user):
        user.delete()

    @property
    def users(self):
        for user in User.select():
            yield user

    def get_user(self, address):
        found = Address.get_by(address=address)
        return found and found.user
