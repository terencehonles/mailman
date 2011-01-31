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

"""Tests of application level membership functions."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.app.membership import add_member
from mailman.core.constants import system_preferences
from mailman.interfaces.member import DeliveryMode
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



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AddMemberTest))
    return suite
