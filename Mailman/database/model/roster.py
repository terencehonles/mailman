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

from Mailman.Errors import ExistingAddressError
from Mailman.interfaces import IRoster


ADDRESS_KIND    = 'Mailman.database.model.address.Address'
ROSTERSET_KIND  = 'Mailman.database.model.rosterset.RosterSet'


class Roster(Entity):
    implements(IRoster)

    has_field('name', Unicode)
    # Relationships
    has_and_belongs_to_many('addresses', of_kind=ADDRESS_KIND)
    has_and_belongs_to_many('roster_set', of_kind=ROSTERSET_KIND)

    def create(self, email_address, real_name=None):
        """See IRoster"""
        from Mailman.database.model.address import Address
        addr = Address.get_by(address=email_address)
        if addr:
            raise ExistingAddressError(email_address)
        addr = Address(address=email_address, real_name=real_name)
        # Make sure all the expected links are made, including to the null
        # (i.e. everyone) roster.
        self.addresses.append(addr)
        addr.rosters.append(self)
        null_roster = Roster.get_by(name='')
        null_roster.addresses.append(addr)
        addr.rosters.append(null_roster)
        return addr
