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

"""Test the NNTP runner and related utilities."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestNNTP',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.interfaces.nntp import NewsModeration
from mailman.runners import nntp
from mailman.testing.helpers import (
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestNNTP(unittest.TestCase):
    """Test the NNTP runner and related utilities."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._mlist.linked_newsgroup = 'example.test'
        self._msg = mfs("""\
From: anne@example.com
To: test@example.com
Subject: A newsgroup posting
Message-ID: <ant>

Testing
""")

    def test_moderated_approved_header(self):
        # When the mailing list is moderated , the message will get an
        # Approved header, which NNTP software uses to forward to the
        # newsgroup.  The message would not have gotten to the mailing list if
        # it wasn't already approved.
        self._mlist.news_moderation = NewsModeration.moderated
        nntp.prepare_message(self._mlist, self._msg, {})
        self.assertEqual(self._msg['approved'], 'test@example.com')

    def test_open_moderated_approved_header(self):
        # When the mailing list is moderated using an open posting policy, the
        # message will get an Approved header, which NNTP software uses to
        # forward to the newsgroup.  The message would not have gotten to the
        # mailing list if it wasn't already approved.
        self._mlist.news_moderation = NewsModeration.open_moderated
        nntp.prepare_message(self._mlist, self._msg, {})
        self.assertEqual(self._msg['approved'], 'test@example.com')

    def test_moderation_removes_previous_approved_header(self):
        # Any existing Approved header is removed from moderated messages.
        self._msg['Approved'] = 'a bogus approval'
        self._mlist.news_moderation = NewsModeration.moderated
        nntp.prepare_message(self._mlist, self._msg, {})
        headers = self._msg.get_all('approved')
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], 'test@example.com')

    def test_open_moderation_removes_previous_approved_header(self):
        # Any existing Approved header is removed from moderated messages.
        self._msg['Approved'] = 'a bogus approval'
        self._mlist.news_moderation = NewsModeration.open_moderated
        nntp.prepare_message(self._mlist, self._msg, {})
        headers = self._msg.get_all('approved')
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], 'test@example.com')

    def test_stripped_subject(self):
        # The cook-headers handler adds the original and/or stripped (of the
        # prefix) subject to the metadata.  Assume that handler's been run;
        # check the Subject header.
        self._mlist.news_prefix_subject_too = False
        del self._msg['subject']
        self._msg['subject'] = 'Re: Your test'
        msgdata = dict(stripped_subject='Your test')
        nntp.prepare_message(self._mlist, self._msg, msgdata)
        headers = self._msg.get_all('subject')
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], 'Your test')

    def test_original_subject(self):
        # The cook-headers handler adds the original and/or stripped (of the
        # prefix) subject to the metadata.  Assume that handler's been run;
        # check the Subject header.
        self._mlist.news_prefix_subject_too = False
        del self._msg['subject']
        self._msg['subject'] = 'Re: Your test'
        msgdata = dict(original_subject='Your test')
        nntp.prepare_message(self._mlist, self._msg, msgdata)
        headers = self._msg.get_all('subject')
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], 'Your test')

    def test_stripped_subject_prefix_okay(self):
        # The cook-headers handler adds the original and/or stripped (of the
        # prefix) subject to the metadata.  Assume that handler's been run;
        # check the Subject header.
        self._mlist.news_prefix_subject_too = True
        del self._msg['subject']
        self._msg['subject'] = 'Re: Your test'
        msgdata = dict(stripped_subject='Your test')
        nntp.prepare_message(self._mlist, self._msg, msgdata)
        headers = self._msg.get_all('subject')
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], 'Re: Your test')

    def test_original_subject_prefix_okay(self):
        # The cook-headers handler adds the original and/or stripped (of the
        # prefix) subject to the metadata.  Assume that handler's been run;
        # check the Subject header.
        self._mlist.news_prefix_subject_too = True
        del self._msg['subject']
        self._msg['subject'] = 'Re: Your test'
        msgdata = dict(original_subject='Your test')
        nntp.prepare_message(self._mlist, self._msg, msgdata)
        headers = self._msg.get_all('subject')
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], 'Re: Your test')

    def test_add_newsgroups_header(self):
        # Prepared messages get a Newsgroups header.
        msgdata = dict(original_subject='Your test')
        nntp.prepare_message(self._mlist, self._msg, msgdata)
        self.assertEqual(self._msg['newsgroups'], 'example.test')

    def test_add_newsgroups_header_to_existing(self):
        # If the message already has a Newsgroups header, the linked newsgroup
        # gets appended to that value, using comma-space separated lists.
        self._msg['Newsgroups'] = 'foo.test, bar.test'
        msgdata = dict(original_subject='Your test')
        nntp.prepare_message(self._mlist, self._msg, msgdata)
        headers = self._msg.get_all('newsgroups')
        self.assertEqual(len(headers), 1)
        self.assertEqual(headers[0], 'foo.test, bar.test, example.test')

    def test_add_lines_header(self):
        # A Lines: header seems useful.
        nntp.prepare_message(self._mlist, self._msg, {})
        self.assertEqual(self._msg['lines'], '1')

    def test_the_message_has_been_prepared(self):
        msgdata = {}
        nntp.prepare_message(self._mlist, self._msg, msgdata)
        self.assertTrue(msgdata.get('prepped'))
