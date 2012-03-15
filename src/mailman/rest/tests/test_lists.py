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

"""REST list tests."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from urllib2 import HTTPError

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer



class TestListsMissing(unittest.TestCase):
    layer = RESTLayer

    def test_missing_list_roster_member_404(self):
        # /lists/<missing>/roster/member gives 404
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/lists/missing@example.com'
                     '/roster/member')
        except HTTPError as exc:
            self.assertEqual(exc.code, 404)
        else:
            raise AssertionError('Expected HTTPError')

    def test_missing_list_roster_owner_404(self):
        # /lists/<missing>/roster/owner gives 404
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/lists/missing@example.com'
                     '/roster/owner')
        except HTTPError as exc:
            self.assertEqual(exc.code, 404)
        else:
            raise AssertionError('Expected HTTPError')

    def test_missing_list_roster_moderator_404(self):
        # /lists/<missing>/roster/member gives 404
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/lists/missing@example.com'
                     '/roster/moderator')
        except HTTPError as exc:
            self.assertEqual(exc.code, 404)
        else:
            raise AssertionError('Expected HTTPError')

    def test_missing_list_configuration_404(self):
        # /lists/<missing>/config gives 404
        try:
            # For Python 2.6.
            call_api(
                'http://localhost:9001/3.0/lists/missing@example.com/config')
        except HTTPError as exc:
            self.assertEqual(exc.code, 404)
        else:
            raise AssertionError('Expected HTTPError')

class TestLists(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        config.db.commit()
        self._usermanager = getUtility(IUserManager)

    def test_list_members_count(self):
        # The list initially has 0 members
        list_info, response = call_api('http://localhost:9001/3.0/lists/test@example.com')
        if response.status != 200:
            raise AssertionError('Got an error from rest server: {0}'.format(response.status))
        self.assertEqual(list_info['member_count'], 0)

        # Add a member to a list
        alice = self._usermanager.create_address('alice@example.com')
        self._mlist.subscribe(alice)
        config.db.commit()

        # Make sure that the api returns one member now
        list_info, response = call_api('http://localhost:9001/3.0/lists/test@example.com')
        if response.status != 200:
            raise AssertionError('Got an error from rest server: {0}'.format(response.status))
        self.assertEqual(list_info['member_count'], 1)

        # Add a second member to it
        bob = self._usermanager.create_address('bob@example.com')
        self._mlist.subscribe(bob)
        config.db.commit()

        # Make sure that the api returns two members now
        list_info, response = call_api('http://localhost:9001/3.0/lists/test@example.com')
        if response.status != 200:
            raise AssertionError('Got an error from rest server: {0}'.format(response.status))
        self.assertEqual(list_info['member_count'], 2)
