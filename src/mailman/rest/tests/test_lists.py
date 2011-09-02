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

"""REST list tests."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from urllib2 import HTTPError

from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer



class TestLists(unittest.TestCase):
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



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLists))
    return suite
