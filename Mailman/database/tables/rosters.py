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

"""Collections of email addresses.

Rosters contain email addresses.  RosterSets contain Rosters.  Most attributes
on the listdata table take RosterSets so that it's easy to compose just about
any combination of addresses.
"""

from sqlalchemy import *

from Mailman.database.tables.addresses import Address



class Roster(object):
    pass


class RosterSet(object):
    pass



def make_table(metadata, tables):
    table = Table(
        'Rosters', metadata,
        Column('roster_id', Integer, primary_key=True),
        )
    # roster* <-> address*
    props = dict(addresses=
                 relation(Address,
                          secondary=tables.address_rosters,
                          lazy=False))
    mapper(Roster, table, properties=props)
    tables.bind(table)
    table = Table(
        'RosterSets', metadata,
        Column('rosterset_id',  Integer, primary_key=True),
        )
    # rosterset -> roster*
    props = dict(rosters=relation(Roster, cascade='all, delete=orphan'))
    mapper(RosterSet, table, properties=props)
    tables.bind(table)
