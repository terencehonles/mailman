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

"""Test the various pending requests interfaces."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.app.moderator import hold_message
from mailman.interfaces.requests import IListRequests, RequestType
from mailman.testing.helpers import specialized_message_from_string as mfs
from mailman.testing.layers import ConfigLayer



class TestRequests(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('ant@example.com')
        self._msg = mfs("""\
From: anne@example.com
To: ant@example.com
Subject: Something
Message-ID: <alpha>

Something else.
""")

    def test_get_request_with_type(self):
        # get_request() takes an optional request type.
        request_id = hold_message(self._mlist, self._msg)
        requests_db = IListRequests(self._mlist)
        # Submit a request with a non-matching type.  This should return None
        # as if there were no matches.
        response = requests_db.get_request(
            request_id, RequestType.subscription)
        self.assertEqual(response, None)
        # Submit the same request with a matching type.
        key, data = requests_db.get_request(
            request_id, RequestType.held_message)
        self.assertEqual(key, '<alpha>')
        # It should also succeed with no optional request type given.
        key, data = requests_db.get_request(request_id)
        self.assertEqual(key, '<alpha>')
