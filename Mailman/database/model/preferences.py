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
from email.utils import formataddr
from zope.interface import implements

from Mailman.database.types import EnumType
from Mailman.interfaces import IPreferences

ADDRESS_KIND    = 'Mailman.database.model.address.Address'
MEMBER_KIND     = 'Mailman.database.model.member.Member'
USER_KIND       = 'Mailman.database.model.user.User'



class Preferences(Entity):
    implements(IPreferences)

    has_field('acknowledge_posts',      Boolean)
    has_field('hide_address',           Boolean)
    has_field('preferred_language',     Unicode)
    has_field('receive_list_copy',      Boolean)
    has_field('receive_own_postings',   Boolean)
    has_field('delivery_mode',          EnumType)
    has_field('delivery_status',        EnumType)
    # Options
    using_options(shortnames=True)

    def __repr__(self):
        return '<Preferences object at %#x>' % id(self)
