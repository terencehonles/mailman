# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""Tests of application level membership functions."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.app.membership import add_member
from mailman.config import config
from mailman.core.constants import system_preferences
from mailman.interfaces.bans import IBanManager
from mailman.interfaces.member import (
    AlreadySubscribedError, DeliveryMode, MemberRole, MembershipIsBannedError)
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import reset_the_world
from mailman.testing.layers import ConfigLayer



class AddMemberTest(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')

    def tearDown(self):
        reset_the_world()

    def test_add_member_new_user(self):
        # Test subscribing a user to a mailing list when the email address has
        # not yet been associated with a user.
        member = add_member(self._mlist, 'aperson@example.com',
                            'Anne Person', '123', DeliveryMode.regular,
                            system_preferences.preferred_language)
        self.assertEqual(member.address.email, 'aperson@example.com')
        self.assertEqual(member.mailing_list, 'test@example.com')
        self.assertEqual(member.role, MemberRole.member)

    def test_add_member_existing_user(self):
        # Test subscribing a user to a mailing list when the email address has
        # already been associated with a user.
        user_manager = getUtility(IUserManager)
        user_manager.create_user('aperson@example.com', 'Anne Person')
        member = add_member(self._mlist, 'aperson@example.com',
                            'Anne Person', '123', DeliveryMode.regular,
                            system_preferences.preferred_language)
        self.assertEqual(member.address.email, 'aperson@example.com')
        self.assertEqual(member.mailing_list, 'test@example.com')

    def test_add_member_banned(self):
        # Test that members who are banned by specific address cannot
        # subscribe to the mailing list.
        getUtility(IBanManager).ban('anne@example.com', 'test@example.com')
        self.assertRaises(
            MembershipIsBannedError,
            add_member, self._mlist, 'anne@example.com', 'Anne Person',
            '123', DeliveryMode.regular, system_preferences.preferred_language)

    def test_add_member_globally_banned(self):
        # Test that members who are banned by specific address cannot
        # subscribe to the mailing list.
        getUtility(IBanManager).ban('anne@example.com')
        self.assertRaises(
            MembershipIsBannedError,
            add_member, self._mlist, 'anne@example.com', 'Anne Person',
            '123', DeliveryMode.regular, system_preferences.preferred_language)

    def test_add_member_banned_from_different_list(self):
        # Test that members who are banned by specific address cannot
        # subscribe to the mailing list.
        getUtility(IBanManager).ban('anne@example.com', 'sample@example.com')
        member = add_member(self._mlist, 'anne@example.com',
                            'Anne Person', '123', DeliveryMode.regular,
                            system_preferences.preferred_language)
        self.assertEqual(member.address.email, 'anne@example.com')

    def test_add_member_banned_by_pattern(self):
        # Test that members who are banned by specific address cannot
        # subscribe to the mailing list.
        getUtility(IBanManager).ban('^.*@example.com', 'test@example.com')
        self.assertRaises(
            MembershipIsBannedError,
            add_member, self._mlist, 'anne@example.com', 'Anne Person',
            '123', DeliveryMode.regular, system_preferences.preferred_language)

    def test_add_member_globally_banned_by_pattern(self):
        # Test that members who are banned by specific address cannot
        # subscribe to the mailing list.
        getUtility(IBanManager).ban('^.*@example.com')
        self.assertRaises(
            MembershipIsBannedError,
            add_member, self._mlist, 'anne@example.com', 'Anne Person',
            '123', DeliveryMode.regular, system_preferences.preferred_language)

    def test_add_member_banned_from_different_list_by_pattern(self):
        # Test that members who are banned by specific address cannot
        # subscribe to the mailing list.
        getUtility(IBanManager).ban('^.*@example.com', 'sample@example.com')
        member = add_member(self._mlist, 'anne@example.com',
                            'Anne Person', '123', DeliveryMode.regular,
                            system_preferences.preferred_language)
        self.assertEqual(member.address.email, 'anne@example.com')

    def test_add_member_moderator(self):
        # Test adding a moderator to a mailing list.
        member = add_member(self._mlist, 'aperson@example.com',
                            'Anne Person', '123', DeliveryMode.regular,
                            system_preferences.preferred_language,
                            MemberRole.moderator)
        self.assertEqual(member.address.email, 'aperson@example.com')
        self.assertEqual(member.mailing_list, 'test@example.com')
        self.assertEqual(member.role, MemberRole.moderator)
    
    def test_add_member_twice(self):
        # Adding a member with the same role twice causes an
        # AlreadySubscribedError to be raised.
        add_member(self._mlist, 'aperson@example.com',
                   'Anne Person', '123', DeliveryMode.regular,
                   system_preferences.preferred_language,
                   MemberRole.member)
        try:
            add_member(self._mlist, 'aperson@example.com',
                       'Anne Person', '123', DeliveryMode.regular,
                       system_preferences.preferred_language,
                       MemberRole.member)
        except AlreadySubscribedError as exc:
            self.assertEqual(exc.fqdn_listname, 'test@example.com')
            self.assertEqual(exc.email, 'aperson@example.com')
            self.assertEqual(exc.role, MemberRole.member)
        else:
            raise AssertionError('AlreadySubscribedError expected')

    def test_add_member_with_different_roles(self):
        # Adding a member twice with different roles is okay.
        member_1 = add_member(self._mlist, 'aperson@example.com',
                              'Anne Person', '123', DeliveryMode.regular,
                              system_preferences.preferred_language,
                              MemberRole.member)
        member_2 = add_member(self._mlist, 'aperson@example.com',
                              'Anne Person', '123', DeliveryMode.regular,
                              system_preferences.preferred_language,
                              MemberRole.owner)
        self.assertEqual(member_1.mailing_list, member_2.mailing_list)
        self.assertEqual(member_1.address, member_2.address)
        self.assertEqual(member_1.user, member_2.user)
        self.assertNotEqual(member_1.member_id, member_2.member_id)
        self.assertEqual(member_1.role, MemberRole.member)
        self.assertEqual(member_2.role, MemberRole.owner)



class AddMemberPasswordTest(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        # The default ssha scheme introduces a random salt, which is
        # inappropriate for unit tests.
        config.push('password scheme', """
        [passwords]
        password_scheme: sha
        """)

    def tearDown(self):
        config.pop('password scheme')
        reset_the_world()

    def test_add_member_password(self):
        # Test that the password stored with the new user is encrypted.
        member = add_member(self._mlist, 'anne@example.com',
                            'Anne Person', 'abc', DeliveryMode.regular,
                            system_preferences.preferred_language)
        self.assertEqual(
            member.user.password, '{SHA}qZk-NkcGgWq6PiVxeFDCbJzQ2J0=')
