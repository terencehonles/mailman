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

"""Email addresses."""

from sqlalchemy import *



class Address(object):
    pass


def make_table(metadata, tables):
    address_table = Table(
        'Addresses', metadata,
        Column('address_id',    Integer, primary_key=True),
        Column('profile_id',    Integer, ForeignKey('Profiles.profile_id')),
        Column('address',       Unicode),
        Column('verified',      Boolean),
        Column('bounce_info',   PickleType),
        )
    # Associate Rosters
    address_rosters_table = Table(
        'AddressRoster', metadata,
        Column('roster_id',     Integer, ForeignKey('Rosters.roster_id')),
        Column('address_id',    Integer, ForeignKey('Addresses.address_id')),
        )
    mapper(Address, address_table)
    tables.bind(address_table)
    tables.bind(address_rosters_table, 'address_rosters')
