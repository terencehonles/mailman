# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
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

"""Unit tests for the SafeDict module."""

import email
import unittest

from mailman import SafeDict



class TestSafeDict(unittest.TestCase):
    def test_okay(self):
        sd = SafeDict.SafeDict({'foo': 'bar'})
        si = '%(foo)s' % sd
        self.assertEqual(si, 'bar')

    def test_key_error(self):
        sd = SafeDict.SafeDict({'foo': 'bar'})
        si = '%(baz)s' % sd
        self.assertEqual(si, '%(baz)s')

    def test_key_error_not_string(self):
        key = ()
        sd = SafeDict.SafeDict({})
        self.assertEqual(sd[key], '<Missing key: ()>')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSafeDict))
    return suite
