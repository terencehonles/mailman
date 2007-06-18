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
PREFERENCE_KIND = 'Mailman.database.model.preferences.Preferences'



class Member(Entity):
    implements(IMember)

    has_field('role',           EnumType)
    has_field('mailing_list',   Unicode)
    # Relationships
    belongs_to('address',       of_kind=ADDRESS_KIND)
    belongs_to('preferences',   of_kind=PREFERENCE_KIND)
    # Options
    using_options(shortnames=True)

    def __repr__(self):
        return '<Member: %s on %s as %s>' % (
            self.address, self.mailing_list, self.role)

    def _lookup(self, preference):
        pref = getattr(self.preferences, preference)
        if pref is not None:
            return pref
        pref = getattr(self.address.preferences, preference)
        if pref is not None:
            return pref
        if self.address.user:
            pref = getattr(self.address.user.preferences, preference)
            if pref is not None:
                return pref
        return getattr(SystemDefaultPreferences, preference)

    @property
    def delivery_mode(self):
        return self._lookup('delivery_mode')

    @property
    def acknowledge_posts(self):
        return self._lookup('acknowledge_posts')

    @property
    def preferred_language(self):
        return self._lookup('preferred_language')

    def unsubscribe(self):
        self.preferences.delete()
        self.delete()

    @property
    def options_url(self):
        # XXX Um, this is definitely wrong
        return 'http://example.com/' + self.address.address
