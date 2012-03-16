# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""Test rosters."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestMailingListRoster',
    'TestMembershipsRoster',
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.interfaces.member import DeliveryMode, MemberRole
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.layers import ConfigLayer
from mailman.utilities.datetime import now



class TestMailingListRoster(unittest.TestCase):
    """Test various aspects of a mailing list's roster."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        user_manager = getUtility(IUserManager)
        self._anne = user_manager.create_address('anne@example.com')
        self._bart = user_manager.create_address('bart@example.com')
        self._cris = user_manager.create_address('cris@example.com')

    def test_no_members(self):
        # Nobody with any role is subscribed to the mailing list.
        self.assertEqual(self._mlist.owners.member_count, 0)
        self.assertEqual(self._mlist.moderators.member_count, 0)
        self.assertEqual(self._mlist.administrators.member_count, 0)
        self.assertEqual(self._mlist.members.member_count, 0)
        self.assertEqual(self._mlist.regular_members.member_count, 0)
        self.assertEqual(self._mlist.digest_members.member_count, 0)
        self.assertEqual(self._mlist.subscribers.member_count, 0)

    def test_one_regular_member(self):
        # One person getting regular delivery is subscribed to the mailing
        # list as a member.
        self._mlist.subscribe(self._anne, role=MemberRole.member)
        self.assertEqual(self._mlist.owners.member_count, 0)
        self.assertEqual(self._mlist.moderators.member_count, 0)
        self.assertEqual(self._mlist.administrators.member_count, 0)
        self.assertEqual(self._mlist.members.member_count, 1)
        self.assertEqual(self._mlist.regular_members.member_count, 1)
        self.assertEqual(self._mlist.digest_members.member_count, 0)
        self.assertEqual(self._mlist.subscribers.member_count, 1)

    def test_two_regular_members(self):
        # Two people getting regular delivery are subscribed to the mailing
        # list as members.
        self._mlist.subscribe(self._anne, role=MemberRole.member)
        self._mlist.subscribe(self._bart, role=MemberRole.member)
        self.assertEqual(self._mlist.owners.member_count, 0)
        self.assertEqual(self._mlist.moderators.member_count, 0)
        self.assertEqual(self._mlist.administrators.member_count, 0)
        self.assertEqual(self._mlist.members.member_count, 2)
        self.assertEqual(self._mlist.regular_members.member_count, 2)
        self.assertEqual(self._mlist.digest_members.member_count, 0)
        self.assertEqual(self._mlist.subscribers.member_count, 2)

    def test_one_regular_members_one_digest_member(self):
        # Two people are subscribed to the mailing list as members.  One gets
        # regular delivery and one gets digest delivery.
        self._mlist.subscribe(self._anne, role=MemberRole.member)
        member = self._mlist.subscribe(self._bart, role=MemberRole.member)
        member.preferences.delivery_mode = DeliveryMode.mime_digests
        self.assertEqual(self._mlist.owners.member_count, 0)
        self.assertEqual(self._mlist.moderators.member_count, 0)
        self.assertEqual(self._mlist.administrators.member_count, 0)
        self.assertEqual(self._mlist.members.member_count, 2)
        self.assertEqual(self._mlist.regular_members.member_count, 1)
        self.assertEqual(self._mlist.digest_members.member_count, 1)
        self.assertEqual(self._mlist.subscribers.member_count, 2)

    def test_a_person_is_both_a_member_and_an_owner(self):
        # Anne is the owner of a mailing list and she gets subscribed as a
        # member of the mailing list, receiving regular deliveries.
        self._mlist.subscribe(self._anne, role=MemberRole.member)
        self._mlist.subscribe(self._anne, role=MemberRole.owner)
        self.assertEqual(self._mlist.owners.member_count, 1)
        self.assertEqual(self._mlist.moderators.member_count, 0)
        self.assertEqual(self._mlist.administrators.member_count, 1)
        self.assertEqual(self._mlist.members.member_count, 1)
        self.assertEqual(self._mlist.regular_members.member_count, 1)
        self.assertEqual(self._mlist.digest_members.member_count, 0)
        self.assertEqual(self._mlist.subscribers.member_count, 2)

    def test_a_bunch_of_members_and_administrators(self):
        # Anne is the owner of a mailing list, and Bart is a moderator.  Anne
        # gets subscribed as a member of the mailing list, receiving regular
        # deliveries.  Cris subscribes to the mailing list as a digest member.
        self._mlist.subscribe(self._anne, role=MemberRole.owner)
        self._mlist.subscribe(self._bart, role=MemberRole.moderator)
        self._mlist.subscribe(self._anne, role=MemberRole.member)
        member = self._mlist.subscribe(self._cris, role=MemberRole.member)
        member.preferences.delivery_mode = DeliveryMode.mime_digests
        self.assertEqual(self._mlist.owners.member_count, 1)
        self.assertEqual(self._mlist.moderators.member_count, 1)
        self.assertEqual(self._mlist.administrators.member_count, 2)
        self.assertEqual(self._mlist.members.member_count, 2)
        self.assertEqual(self._mlist.regular_members.member_count, 1)
        self.assertEqual(self._mlist.digest_members.member_count, 1)
        self.assertEqual(self._mlist.subscribers.member_count, 4)



class TestMembershipsRoster(unittest.TestCase):
    """Test the memberships roster."""

    layer = ConfigLayer

    def setUp(self):
        self._ant = create_list('ant@example.com')
        self._bee = create_list('bee@example.com')
        user_manager = getUtility(IUserManager)
        self._anne = user_manager.create_user('anne@example.com')
        preferred = list(self._anne.addresses)[0]
        preferred.verified_on = now()
        self._anne.preferred_address = preferred

    def test_no_memberships(self):
        # An unsubscribed user has no memberships.
        self.assertEqual(self._anne.memberships.member_count, 0)

    def test_subscriptions(self):
        # Anne subscribes to a couple of mailing lists.
        self._ant.subscribe(self._anne)
        self._bee.subscribe(self._anne)
        self.assertEqual(self._anne.memberships.member_count, 2)
