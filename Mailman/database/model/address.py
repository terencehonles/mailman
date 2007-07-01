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

from Mailman.interfaces import IAddress

MEMBER_KIND     = 'Mailman.database.model.member.Member'
PREFERENCE_KIND = 'Mailman.database.model.preferences.Preferences'
USER_KIND       = 'Mailman.database.model.user.User'



class Address(Entity):
    implements(IAddress)

    has_field('address',        Unicode)
    has_field('_original',      Unicode)
    has_field('real_name',      Unicode)
    has_field('verified',       Boolean)
    has_field('registered_on',  DateTime)
    has_field('validated_on',   DateTime)
    # Relationships
    belongs_to('user',          of_kind=USER_KIND)
    belongs_to('preferences',   of_kind=PREFERENCE_KIND)
    # Options
    using_options(shortnames=True)

    def __init__(self, address, real_name):
        super(Address, self).__init__()
        lower_case = address.lower()
        self.address = lower_case
        self.real_name = real_name
        self._original = (None if lower_case == address else address)

    def __str__(self):
        addr = (self.address if self._original is None else self._original)
        return formataddr((self.real_name, addr))

    def __repr__(self):
        verified = ('verified' if self.verified else 'not verified')
        address_str = str(self)
        if self._original is None:
            return '<Address: %s [%s] at %#x>' % (
                address_str, verified, id(self))
        else:
            return '<Address: %s [%s] key: %s at %#x>' % (
                address_str, verified, self.address, id(self))

    def subscribe(self, mlist, role):
        from Mailman.database.model import Member
        from Mailman.database.model import Preferences
        # This member has no preferences by default.
        member = Member(role=role,
                        mailing_list=mlist.fqdn_listname,
                        address=self)
        member.preferences = Preferences()
        return member

    @property
    def original_address(self):
        return (self.address if self._original is None else self._original)
