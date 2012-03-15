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

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestLists',
    'TestListsMissing',
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
    """Test expected failures."""

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
    """Test various aspects of mailing list resources."""

    layer = RESTLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        config.db.commit()
        self._usermanager = getUtility(IUserManager)

    def test_member_count_with_no_members(self):
        # The list initially has 0 members.
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/test@example.com')
        self.assertEqual(response.status, 200)
        self.assertEqual(resource['member_count'], 0)

    def test_member_count_with_one_member(self):
        # Add a member to a list and check that the resource reflects this.
        anne = self._usermanager.create_address('anne@example.com')
        self._mlist.subscribe(anne)
        config.db.commit()
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/test@example.com')
        self.assertEqual(response.status, 200)
        self.assertEqual(resource['member_count'], 1)

    def test_member_count_with_two_members(self):
        # Add two members to a list and check that the resource reflects this.
        anne = self._usermanager.create_address('anne@example.com')
        self._mlist.subscribe(anne)
        bart = self._usermanager.create_address('bar@example.com')
        self._mlist.subscribe(bart)
        config.db.commit()
        resource, response = call_api(
            'http://localhost:9001/3.0/lists/test@example.com')
        self.assertEqual(response.status, 200)
        self.assertEqual(resource['member_count'], 2)
