# Copyright (C) 2006-2009 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Model for addresses."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Address',
    ]


from email.utils import formataddr
from storm.locals import DateTime, Int, Reference, Store, Unicode
from zope.interface import implements

from mailman.database.model import Model
from mailman.interfaces.member import AlreadySubscribedError
from mailman.interfaces.address import IAddress
from mailman.model.member import Member
from mailman.model.preferences import Preferences



class Address(Model):
    implements(IAddress)

    id = Int(primary=True)
    address = Unicode()
    _original = Unicode()
    real_name = Unicode()
    verified_on = DateTime()
    registered_on = DateTime()

    user_id = Int()
    user = Reference(user_id, 'User.id')
    preferences_id = Int()
    preferences = Reference(preferences_id, 'Preferences.id')

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
        verified = ('verified' if self.verified_on else 'not verified')
        address_str = str(self)
        if self._original is None:
            return '<Address: {0} [{1}] at {2:#x}>'.format(
                address_str, verified, id(self))
        else:
            return '<Address: {0} [{1}] key: {2} at {3:#x}>'.format(
                address_str, verified, self.address, id(self))

    def subscribe(self, mailing_list, role):
        # This member has no preferences by default.
        store = Store.of(self)
        member = store.find(
            Member,
            Member.role == role,
            Member.mailing_list == mailing_list.fqdn_listname,
            Member.address == self).one()
        if member:
            raise AlreadySubscribedError(
                mailing_list.fqdn_listname, self.address, role)
        member = Member(role=role,
                        mailing_list=mailing_list.fqdn_listname,
                        address=self)
        member.preferences = Preferences()
        store.add(member)
        return member

    @property
    def original_address(self):
        return (self.address if self._original is None else self._original)
