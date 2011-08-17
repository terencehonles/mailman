# Copyright (C) 2011 by the Free Software Foundation, Inc.
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

"""Test members."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.member import MembershipError
from mailman.interfaces.subscriptions import ISubscriptionService
from mailman.interfaces.user import UnverifiedAddressError
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.layers import ConfigLayer
from mailman.utilities.datetime import now

from zope.component import getUtility



class TestMember(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._usermanager = getUtility(IUserManager)

    def test_cannot_set_address_with_preferred_address_subscription(self):
        # A user is subscribed to a mailing list with their preferred address.
        # You cannot set the `address` attribute on such IMembers.
        anne = self._usermanager.create_user('anne@example.com')
        preferred = list(anne.addresses)[0]
        preferred.verified_on = now()
        anne.preferred_address = preferred
        # Subscribe with the IUser object, not the address.  This makes Anne a
        # member via her preferred address.
        member = self._mlist.subscribe(anne)
        new_address = anne.register('aperson@example.com')
        new_address.verified_on = now()
        self.assertRaises(MembershipError,
                          setattr, member, 'address', new_address)

    def test_cannot_change_to_unverified_address(self):
        # A user is subscribed to a mailing list with an explicit address.
        # You cannot set the `address` attribute to an unverified address.
        anne = self._usermanager.create_user('anne@example.com')
        address = list(anne.addresses)[0]
        member = self._mlist.subscribe(address)
        new_address = anne.register('aperson@example.com')
        # The new address is not verified.
        self.assertRaises(UnverifiedAddressError,
                          setattr, member, 'address', new_address)

    def test_cannot_change_to_address_uncontrolled_address(self):
        # A user tries to change their subscription to an address they do not
        # control.
        anne = self._usermanager.create_user('anne@example.com')
        address = list(anne.addresses)[0]
        member = self._mlist.subscribe(address)
        new_address = self._usermanager.create_address('nobody@example.com')
        new_address.verified_on = now()
        # The new address is not verified.
        self.assertRaises(MembershipError,
                          setattr, member, 'address', new_address)

    def test_cannot_change_to_address_controlled_by_other_user(self):
        # A user tries to change their subscription to an address some other
        # user controls.
        anne = self._usermanager.create_user('anne@example.com')
        anne_address = list(anne.addresses)[0]
        bart = self._usermanager.create_user('bart@example.com')
        bart_address = list(bart.addresses)[0]
        bart_address.verified_on = now()
        member = self._mlist.subscribe(anne_address)
        # The new address is not verified.
        self.assertRaises(MembershipError,
                          setattr, member, 'address', bart_address)



class TestMembership(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._ant = create_list('ant@example.com')
        self._bee = create_list('bee@example.com')
        self._usermanager = getUtility(IUserManager)

    def test_members_are_deleted_when_mailing_list_is_deleted(self):
        # When a mailing list with members is deleted, all the Member records
        # are also deleted.
        anne = self._usermanager.create_address('anne@example.com')
        bart = self._usermanager.create_address('bart@example.com')
        anne_ant = self._ant.subscribe(anne)
        anne_bee = self._bee.subscribe(anne)
        bart_ant = self._ant.subscribe(bart)
        anne_ant_id = anne_ant.member_id
        anne_bee_id = anne_bee.member_id
        bart_ant_id = bart_ant.member_id
        getUtility(IListManager).delete(self._ant)
        service = getUtility(ISubscriptionService)
        # We deleted the ant@example.com mailing list.  Anne's and Bart's
        # membership in this list should now be removed, but Anne's membership
        # in bee@example.com should still exist.
        self.assertEqual(service.get_member(anne_ant_id), None)
        self.assertEqual(service.get_member(bart_ant_id), None)
        self.assertEqual(service.get_member(anne_bee_id), anne_bee)



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMember))
    suite.addTest(unittest.makeSuite(TestMembership))
    return suite
