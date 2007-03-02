# Copyright (C) 2007 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Unit tests for Enums."""

import operator
import unittest

from Mailman.enum import Enum



class Colors(Enum):
    red     = 1
    green   = 2
    blue    = 3


class MoreColors(Colors):
    pink    = 4
    cyan    = 5


class OtherColors(Enum):
    red     = 1
    blue    = 2
    yellow  = 3



class TestEnum(unittest.TestCase):
    def test_enum_basics(self):
        unless = self.failUnless
        raises = self.assertRaises
        # Cannot compare by equality
        raises(NotImplementedError, operator.eq, Colors.red, Colors.red)
        raises(NotImplementedError, operator.ne, Colors.red, Colors.red)
        raises(NotImplementedError, operator.lt, Colors.red, Colors.red)
        raises(NotImplementedError, operator.gt, Colors.red, Colors.red)
        raises(NotImplementedError, operator.le, Colors.red, Colors.red)
        raises(NotImplementedError, operator.ge, Colors.red, Colors.red)
        raises(NotImplementedError, operator.eq, Colors.red, 1)
        raises(NotImplementedError, operator.ne, Colors.red, 1)
        raises(NotImplementedError, operator.lt, Colors.red, 1)
        raises(NotImplementedError, operator.gt, Colors.red, 1)
        raises(NotImplementedError, operator.le, Colors.red, 1)
        raises(NotImplementedError, operator.ge, Colors.red, 1)
        # Comparison by identity
        unless(Colors.red is Colors.red)
        unless(Colors.red is MoreColors.red)
        unless(Colors.red is not OtherColors.red)
        unless(Colors.red is not Colors.blue)

    def test_enum_conversions(self):
        eq = self.assertEqual
        unless = self.failUnless
        raises = self.assertRaises
        unless(Colors.red is Colors['red'])
        unless(Colors.red is Colors[1])
        unless(Colors.red is Colors('red'))
        unless(Colors.red is Colors(1))
        unless(Colors.red is not Colors['blue'])
        unless(Colors.red is not Colors[2])
        unless(Colors.red is not Colors('blue'))
        unless(Colors.red is not Colors(2))
        unless(Colors.red is MoreColors['red'])
        unless(Colors.red is MoreColors[1])
        unless(Colors.red is MoreColors('red'))
        unless(Colors.red is MoreColors(1))
        unless(Colors.red is not OtherColors['red'])
        unless(Colors.red is not OtherColors[1])
        unless(Colors.red is not OtherColors('red'))
        unless(Colors.red is not OtherColors(1))
        raises(ValueError, Colors.__getitem__, 'magenta')
        raises(ValueError, Colors.__getitem__, 99)
        raises(ValueError, Colors.__call__, 'magenta')
        raises(ValueError, Colors.__call__, 99)
        eq(int(Colors.red), 1)
        eq(int(Colors.blue), 3)
        eq(int(MoreColors.red), 1)
        eq(int(OtherColors.blue), 2)
        

    def test_enum_duplicates(self):
        try:
            class Bad(Enum):
                cartman = 1
                stan    = 2
                kyle    = 3
                kenny   = 3
                butters = 4
        except TypeError:
            got_error = True
        else:
            got_error = False
        self.failUnless(got_error)



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEnum))
    return suite
