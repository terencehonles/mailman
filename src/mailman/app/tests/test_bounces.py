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

"""Testing app.bounces functions."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from mailman.app.bounces import get_verp
from mailman.app.lifecycle import create_list
from mailman.testing.helpers import (
    specialized_message_from_string as message_from_string)
from mailman.testing.layers import ConfigLayer



class TestVERP(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')

    def test_no_verp(self):
        # The empty set is returned when there is no VERP headers.
        msg = message_from_string("""\
From: postmaster@example.com
To: mailman-bounces@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg), set())

    def test_verp_in_to(self):
        # A VERP address is found in the To header.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg), set(['anne@example.org']))

    def test_verp_in_delivered_to(self):
        # A VERP address is found in the Delivered-To header.
        msg = message_from_string("""\
From: postmaster@example.com
Delivered-To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg), set(['anne@example.org']))

    def test_verp_in_envelope_to(self):
        # A VERP address is found in the Envelope-To header.
        msg = message_from_string("""\
From: postmaster@example.com
Envelope-To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg), set(['anne@example.org']))

    def test_verp_in_apparently_to(self):
        # A VERP address is found in the Apparently-To header.
        msg = message_from_string("""\
From: postmaster@example.com
Apparently-To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg), set(['anne@example.org']))

    def test_verp_with_empty_header(self):
        # A VERP address is found, but there's an empty header.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
To:

""")
        self.assertEqual(get_verp(self._mlist, msg), set(['anne@example.org']))

    def test_no_verp_with_empty_header(self):
        # There's an empty header, and no VERP address is found.
        msg = message_from_string("""\
From: postmaster@example.com
To:

""")
        self.assertEqual(get_verp(self._mlist, msg), set())

    def test_verp_with_non_match(self):
        # A VERP address is found, but a header had a non-matching pattern.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
To: test-bounces@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg), set(['anne@example.org']))

    def test_no_verp_with_non_match(self):
        # No VERP address is found, and a header had a non-matching pattern.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg), set())

    def test_multiple_verps(self):
        # More than one VERP address was found in the same header.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
To: test-bounces+anne=example.org@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg), set(['anne@example.org']))

    def test_multiple_verps_different_values(self):
        # More than one VERP address was found in the same header with
        # different values.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
To: test-bounces+bart=example.org@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg),
                         set(['anne@example.org', 'bart@example.org']))

    def test_multiple_verps_different_values_different_headers(self):
        # More than one VERP address was found in different headers with
        # different values.
        msg = message_from_string("""\
From: postmaster@example.com
To: test-bounces+anne=example.org@example.com
Apparently-To: test-bounces+bart=example.org@example.com

""")
        self.assertEqual(get_verp(self._mlist, msg),
                         set(['anne@example.org', 'bart@example.org']))



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestVERP))
    return suite
