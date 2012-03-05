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

"""Scrubber module tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestScrubber',
    ]


import unittest

from mailman.pipeline import scrubber



class TestScrubber(unittest.TestCase):
    """Scrubber module tests."""

    def test_guess_extension(self):
        # A known extension should be found.
        extension = scrubber.guess_extension('application/msword', '.doc')
        self.assertEqual(extension, '.doc')

    def test_guess_missing_extension(self):
        # Maybe some other extension is better.
        extension = scrubber.guess_extension('application/msword', '.xxx')
        self.assertEqual(extension, '.doc')
