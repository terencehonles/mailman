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

"""REST membership tests."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from urllib2 import HTTPError
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer



class TestMembership(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        config.db.commit()
        self._usermanager = getUtility(IUserManager)

    def test_try_to_join_missing_list(self):
        # A user tries to join a non-existent list.
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/members', {
                'fqdn_listname': 'missing@example.com',
                'address': 'nobody@example.com',
                })
        except HTTPError as exc:
            self.assertEqual(exc.code, 400)
            self.assertEqual(exc.msg, 'No such list')
        else:
            raise AssertionError('Expected HTTPError')

    def test_try_to_leave_missing_list(self):
        # A user tries to leave a non-existent list.
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/lists/missing@example.com'
                     '/member/nobody@example.com',
                     method='DELETE')
        except HTTPError as exc:
            self.assertEqual(exc.code, 404)
            self.assertEqual(exc.msg, '404 Not Found')
        else:
            raise AssertionError('Expected HTTPError')
        
    def test_try_to_leave_list_with_bogus_address(self):
        # Try to leave a mailing list using an invalid membership address.
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/lists/test@example.com'
                     '/member/nobody',
                     method='DELETE')
        except HTTPError as exc:
            self.assertEqual(exc.code, 404)
            self.assertEqual(exc.msg, '404 Not Found')
        else:
            raise AssertionError('Expected HTTPError')

    def test_try_to_leave_a_list_twice(self):
        anne = self._usermanager.create_address('anne@example.com')
        self._mlist.subscribe(anne)
        config.db.commit()
        url = ('http://localhost:9001/3.0/lists/test@example.com'
               '/member/anne@example.com')
        content, response = call_api(url, method='DELETE')
        # For a successful DELETE, the response code is 200 and there is no
        # content.
        self.assertEqual(content, None)
        self.assertEqual(response.status, 200)
        try:
            # For Python 2.6.
            call_api(url, method='DELETE')
        except HTTPError as exc:
            self.assertEqual(exc.code, 404)
            self.assertEqual(exc.msg, '404 Not Found')
        else:
            raise AssertionError('Expected HTTPError')

    def test_try_to_join_a_list_twice(self):
        anne = self._usermanager.create_address('anne@example.com')
        self._mlist.subscribe(anne)
        config.db.commit()
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/members', {
                'fqdn_listname': 'test@example.com',
                'address': 'anne@example.com',
                })
        except HTTPError as exc:
            self.assertEqual(exc.code, 409)
            self.assertEqual(exc.msg, 'Member already subscribed')
        else:
            raise AssertionError('Expected HTTPError')

    def test_join_with_invalid_delivery_mode(self):
        try:
            call_api('http://localhost:9001/3.0/members', {
                'fqdn_listname': 'test@example.com',
                'address': 'anne@example.com',
                'real_name': 'Anne Person',
                'delivery_mode': 'invalid-mode',
                })
        except HTTPError as exc:
            self.assertEqual(exc.code, 400)
            self.assertEqual(exc.msg,
                             'Cannot convert parameters: delivery_mode')
        else:
            raise AssertionError('Expected HTTPError')

    def test_join_email_contains_slash(self):
        content, response = call_api('http://localhost:9001/3.0/members', {
            'fqdn_listname': 'test@example.com',
            'address': 'hugh/person@example.com',
            'real_name': 'Hugh Person',
            })
        self.assertEqual(content, None)
        self.assertEqual(response.status, 201)
        self.assertEqual(response['location'],
                         'http://localhost:9001/3.0/lists/test@example.com'
                         '/member/hugh%2Fperson@example.com')
        # Reset any current transaction.
        config.db.abort()
        members = list(self._mlist.members.members)
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].address.email, 'hugh/person@example.com')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMembership))
    return suite
