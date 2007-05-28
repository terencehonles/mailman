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

"""Mailman user profile information."""

from sqlalchemy import *

from Mailman import Defaults



class Profile(object):
    pass



# Both of these Enum types are stored in the database as integers, and
# converted back into their enums on retrieval.

class DeliveryModeType(types.TypeDecorator):
    impl = types.Integer

    def convert_bind_param(self, value, engine):
        return int(value)

    def convert_result_value(self, value, engine):
        return Defaults.DeliveryMode(value)


class DeliveryStatusType(types.TypeDecorator):
    impl = types.Integer

    def convert_bind_param(self, value, engine):
        return int(value)

    def convert_result_value(self, value, engine):
        return Defaults.DeliveryStatus(value)



def make_table(metadata, tables):
    table = Table(
        'Profiles', metadata,
        Column('profile_id',            Integer, primary_key=True),
        # OldStyleMemberships attributes, temporarily stored as pickles.
        Column('ack',                   Boolean),
        Column('delivery_mode',         DeliveryModeType),
        Column('delivery_status',       DeliveryStatusType),
        Column('hide',                  Boolean),
        Column('language',              Unicode),
        Column('nodupes',               Boolean),
        Column('nomail',                Boolean),
        Column('notmetoo',              Boolean),
        Column('password',              Unicode),
        Column('realname',              Unicode),
        Column('topics',                PickleType),
        )
    # Avoid circular references
    from Mailman.database.tables.addresses import Address
    # profile -> address*
    props = dict(addresses=relation(Address, cascade='all, delete-orphan'))
    mapper(Profile, table, properties=props)
    tables.bind(table)
