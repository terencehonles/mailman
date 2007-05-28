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

from elixir import *
from zope.interface import implements

from Mailman.interfaces import IRosterSet

ROSTER_KIND = 'Mailman.database.model.roster.Roster'



# Internal implementation of roster sets for use with mailing lists.  These
# are owned by the user storage.
class RosterSet(Entity):
    implements(IRosterSet)

    has_field('name',   Unicode)
    has_and_belongs_to_many('rosters', of_kind=ROSTER_KIND)

    def add(self, roster):
        if roster not in self.rosters:
            self.rosters.append(roster)

    def delete(self, roster):
        if roster in self.rosters:
            self.rosters.remove(roster)
