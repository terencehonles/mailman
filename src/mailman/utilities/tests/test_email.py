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

from mailman.utilities.email import split_email



class TestEmail(unittest.TestCase):
    def test_normal_split(self):
        self.assertEqual(split_email('anne@example.com'),
                         ('anne', ['example', 'com']))
        self.assertEqual(split_email('anne@foo.example.com'),
                         ('anne', ['foo', 'example', 'com']))

    def test_no_at_split(self):
        self.assertEqual(split_email('anne'), ('anne', None))



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEmail))
    return suite
