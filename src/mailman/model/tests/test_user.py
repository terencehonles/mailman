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

"""Test users."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'TestUser',
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.layers import ConfigLayer
from mailman.utilities.datetime import now



class TestUser(unittest.TestCase):
    """Test users."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._anne = getUtility(IUserManager).create_user(
            'anne@example.com', 'Anne Person')
        preferred = list(self._anne.addresses)[0]
        preferred.verified_on = now()
        self._anne.preferred_address = preferred

    def test_preferred_address_memberships(self):
        self._mlist.subscribe(self._anne)
        memberships = list(self._anne.memberships.members)
        self.assertEqual(len(memberships), 1)
        self.assertEqual(memberships[0].address.email, 'anne@example.com')
        self.assertEqual(memberships[0].user, self._anne)
        addresses = list(self._anne.memberships.addresses)
        self.assertEqual(len(addresses), 1)
        self.assertEqual(addresses[0].email, 'anne@example.com')

    def test_preferred_and_address_memberships(self):
        self._mlist.subscribe(self._anne)
        aperson = self._anne.register('aperson@example.com')
        self._mlist.subscribe(aperson)
        memberships = list(self._anne.memberships.members)
        self.assertEqual(len(memberships), 2)
        self.assertEqual(set(member.address.email for member in memberships),
                         set(['anne@example.com', 'aperson@example.com']))
        self.assertEqual(memberships[0].user, memberships[1].user)
        self.assertEqual(memberships[0].user, self._anne)
        emails = set(address.email
                     for address in self._anne.memberships.addresses)
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails,
                         set(['anne@example.com', 'aperson@example.com']))
