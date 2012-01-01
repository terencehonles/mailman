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

"""REST address tests."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from urllib2 import HTTPError

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.testing.helpers import call_api
from mailman.testing.layers import RESTLayer



class TestAddresses(unittest.TestCase):
    layer = RESTLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        config.db.commit()

    def test_membership_of_missing_address(self):
        # Try to get the memberships of a missing address.
        try:
            # For Python 2.6.
            call_api('http://localhost:9001/3.0/addresses/'
                     'nobody@example.com/memberships')
        except HTTPError as exc:
            self.assertEqual(exc.code, 404)
        else:
            raise AssertionError('Expected HTTPError')
