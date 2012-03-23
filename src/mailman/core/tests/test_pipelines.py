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

"""Test the core modification pipelines."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestOwnerPipeline',
    'TestPostingPipeline',
    ]


import unittest

from zope.component import getUtility
from zope.interface import implements

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.core.errors import DiscardMessage, RejectMessage
from mailman.core.pipelines import process
from mailman.interfaces.handler import IHandler
from mailman.interfaces.member import MemberRole
from mailman.interfaces.pipeline import IPipeline
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import (
    LogFileMark,
    get_queue_messages,
    reset_the_world,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class DiscardingHandler:
    implements(IHandler)
    name = 'discarding'

    def process(self, mlist, msg, msgdata):
        raise DiscardMessage('by test handler')


class RejectHandler:
    implements(IHandler)
    name = 'rejecting'

    def process(self, mlist, msg, msgdata):
        raise RejectMessage('by test handler')


class DiscardingPipeline:
    implements(IPipeline)
    name = 'test-discarding'
    description = 'Discarding test pipeline'

    def __iter__(self):
        yield DiscardingHandler()


class RejectingPipeline:
    implements(IPipeline)
    name = 'test-rejecting'
    description = 'Rejectinging test pipeline'

    def __iter__(self):
        yield RejectHandler()



class TestPostingPipeline(unittest.TestCase):
    """Test various aspects of the built-in postings pipeline."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        config.pipelines['test-discarding'] = DiscardingPipeline()
        config.pipelines['test-rejecting'] = RejectingPipeline()
        self._msg = mfs("""\
From: Anne Person <anne@example.org>
To: test@example.com
Subject: a test
Message-ID: <ant>

testing
""")

    def tearDown(self):
        reset_the_world()
        del config.pipelines['test-discarding']
        del config.pipelines['test-rejecting']

    def test_rfc2369_headers(self):
        # Ensure that RFC 2369 List-* headers are added.
        msgdata = {}
        process(self._mlist, self._msg, msgdata,
                pipeline_name='default-posting-pipeline')
        self.assertEqual(self._msg['list-id'], '<test.example.com>')
        self.assertEqual(self._msg['list-post'], '<mailto:test@example.com>')

    def test_discarding_pipeline(self):
        # If a handler in the pipeline raises DiscardMessage, the message will
        # be thrown away, but with a log message.
        mark = LogFileMark('mailman.vette')
        process(self._mlist, self._msg, {}, 'test-discarding')
        line = mark.readline()[:-1]
        self.assertTrue(line.endswith(
            '<ant> discarded by "test-discarding" pipeline handler '
            '"discarding": by test handler'))

    def test_rejecting_pipeline(self):
        # If a handler in the pipeline raises DiscardMessage, the message will
        # be thrown away, but with a log message.
        mark = LogFileMark('mailman.vette')
        process(self._mlist, self._msg, {}, 'test-rejecting')
        line = mark.readline()[:-1]
        self.assertTrue(line.endswith(
            '<ant> rejected by "test-rejecting" pipeline handler '
            '"rejecting": by test handler'))
        # In the rejection case, the original message will also be in the
        # virgin queue.
        messages = get_queue_messages('virgin')
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0].msg['subject']), 'a test')



class TestOwnerPipeline(unittest.TestCase):
    """Test various aspects of the built-in owner pipeline."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        user_manager = getUtility(IUserManager)
        anne = user_manager.create_address('anne@example.com')
        bart = user_manager.create_address('bart@example.com')
        self._mlist.subscribe(anne, MemberRole.owner)
        self._mlist.subscribe(bart, MemberRole.moderator)
        self._msg = mfs("""\
From: Anne Person <anne@example.org>
To: test-owner@example.com

""")

    def test_calculate_recipients(self):
        # Recipients are the administrators of the mailing list.
        msgdata = dict(listname='test@example.com',
                       to_owner=True)
        process(self._mlist, self._msg, msgdata,
                pipeline_name='default-owner-pipeline')
        self.assertEqual(msgdata['recipients'], set(('anne@example.com',
                                                     'bart@example.com')))

    def test_to_outgoing(self):
        # The message, with the calculated recipients, gets put in the
        # outgoing queue.
        process(self._mlist, self._msg, {},
                pipeline_name='default-owner-pipeline')
        messages = get_queue_messages('out', sort_on='to')
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].msgdata['recipients'], 
                         set(('anne@example.com', 'bart@example.com')))
