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

"""REST domain tests."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from urllib2 import HTTPError
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.listmanager import IListManager
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer



class TestDomains(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        config.db.commit()

    def test_bogus_endpoint_extension(self):
        # /domains/<domain>/lists/<anything> is not a valid endpoint.
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/domains/example.com'
                     '/lists/wrong')
        except HTTPError as exc:
            self.assertEqual(exc.code, 400)
        else:
            raise AssertionError('Expected HTTPError')

    def test_bogus_endpoint(self):
        # /domains/<domain>/<!lists> does not exist.
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/domains/example.com/wrong')
        except HTTPError as exc:
            self.assertEqual(exc.code, 404)
        else:
            raise AssertionError('Expected HTTPError')

    def test_lists_are_deleted_when_domain_is_deleted(self):
        # /domains/<domain> DELETE removes all associated mailing lists.
        create_list('ant@example.com')
        config.db.commit()
        content, response = call_api(
            'http://localhost:9001/3.0/domains/example.com', method='DELETE')
        self.assertEqual(response.status, 204)
        self.assertEqual(getUtility(IListManager).get('ant@example.com'), None)
