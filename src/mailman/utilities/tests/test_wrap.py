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

"""Test text wrapping."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from mailman.utilities.string import wrap



class TestWrap(unittest.TestCase):
    """Test text wrapping."""

    def test_simple_wrap(self):
        text = """\
This is a single
paragraph.  It consists
of several sentences
none of
which are
very long.
"""
        self.assertEqual(wrap(text), """\
This is a single paragraph.  It consists of several sentences none of
which are very long.""")

    def test_two_paragraphs(self):
        text = """\
This is a single
paragraph.  It consists
of several sentences
none of
which are
very long.

And here is a second paragraph which
also consists
of several sentences. None of
these are very long
either.
"""
        self.assertEqual(wrap(text), """\
This is a single paragraph.  It consists of several sentences none of
which are very long.

And here is a second paragraph which also consists of several
sentences.  None of these are very long either.""")

    def test_honor_ws(self):
        text = """\
This is a single
paragraph.  It consists
of several sentences
none of
which are
very long.

    This paragraph is
    indented so it
    won't be filled.

And here is a second paragraph which
also consists
of several sentences. None of
these are very long
either.
"""
        self.assertEqual(wrap(text), """\
This is a single paragraph.  It consists of several sentences none of
which are very long.

    This paragraph is
    indented so it
    won't be filled.

And here is a second paragraph which also consists of several
sentences.  None of these are very long either.""")

    def test_dont_honor_ws(self):
        text = """\
This is a single
paragraph.  It consists
of several sentences
none of
which are
very long.

    This paragraph is
    indented but we don't
    honor whitespace so it
    will be filled.

And here is a second paragraph which
also consists
of several sentences. None of
these are very long
either.
"""
        self.assertEqual(wrap(text, honor_leading_ws=False), """\
This is a single paragraph.  It consists of several sentences none of
which are very long.

    This paragraph is indented but we don't honor whitespace so it
    will be filled.

And here is a second paragraph which also consists of several
sentences.  None of these are very long either.""")

    def test_indentation_boundary(self):
        text = """\
This is a single paragraph
that consists of one sentence.
    And another one that breaks
    because it is indented.
Followed by one more paragraph.
"""
        self.assertEqual(wrap(text), """\
This is a single paragraph that consists of one sentence.
    And another one that breaks
    because it is indented.
Followed by one more paragraph.""")
