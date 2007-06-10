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

from elixir import *
from zope.interface import implements

from Mailman.Utils import split_listname
from Mailman.constants import SystemDefaultPreferences
from Mailman.database.types import EnumType
from Mailman.interfaces import IMember, IPreferences


ADDRESS_KIND    = 'Mailman.database.model.address.Address'
PREFERENCE_KIND = 'Mailman.database.model.profile.Preferences'



class Member(Entity):
    implements(IMember)

    has_field('role',           EnumType)
    has_field('mailing_list',   Unicode)
    # Relationships
    belongs_to('address',       of_kind=ADDRESS_KIND)
    belongs_to('_preferences',  of_kind=PREFERENCE_KIND)
    # Options
    using_options(shortnames=True)

    def __repr__(self):
        return '<Member: %s on %s as %s>' % (
            self.address, self.mailing_list, self.role)

    @property
    def preferences(self):
        from Mailman.database.model import MailingList
        if self._preferences:
            return self._preferences
        if self.address.preferences:
            return self.address.preferences
        # It's possible this address isn't linked to a user.
        if self.address.user and self.address.user.preferences:
            return self.address.user.preferences
        list_name, host_name = split_listname(self.mailing_list)
        mlist = MailingList.get_by(list_name=list_name,
                                   host_name=host_name)
        if mlist.preferences:
            return mlist.preferences
        return SystemDefaultPreferences
