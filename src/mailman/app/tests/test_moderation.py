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

"""Moderation tests."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestModeration',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.app.moderator import handle_message, hold_message
from mailman.interfaces.action import Action
from mailman.interfaces.requests import IListRequests
from mailman.runners.incoming import IncomingRunner
from mailman.runners.outgoing import OutgoingRunner
from mailman.runners.pipeline import PipelineRunner
from mailman.testing.helpers import (
    make_testable_runner, specialized_message_from_string)
from mailman.testing.layers import SMTPLayer



class TestModeration(unittest.TestCase):
    """Test moderation functionality."""

    layer = SMTPLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._msg = specialized_message_from_string("""\
From: anne@example.com
To: test@example.com
Subject: hold me
Message-ID: <alpha>

""")
        self._in = make_testable_runner(IncomingRunner, 'in')
        self._pipeline = make_testable_runner(PipelineRunner, 'pipeline')
        self._out = make_testable_runner(OutgoingRunner, 'out')
        # Python 2.7 has assertMultiLineEqual.  Let this work without bounds.
        self.maxDiff = None
        self.eq = getattr(self, 'assertMultiLineEqual', self.assertEqual)

    def test_accepted_message_gets_posted(self):
        # A message that is accepted by the moderator should get posted to the
        # mailing list.  LP: #827697
        msgdata = dict(listname='test@example.com',
                       recipients=['bart@example.com'])
        request_id = hold_message(self._mlist, self._msg, msgdata)
        handle_message(self._mlist, request_id, Action.accept)
        self._in.run()
        self._pipeline.run()
        self._out.run()
        messages = list(SMTPLayer.smtpd.messages)
        self.assertEqual(len(messages), 1)
        message = messages[0]
        # We don't need to test the entire posted message, just the bits that
        # prove it got sent out.
        self.assertTrue('x-mailman-version' in message)
        self.assertTrue('x-peer' in message)
        # The X-Mailman-Approved-At header has local timezone information in
        # it, so test that separately.
        self.assertEqual(message['x-mailman-approved-at'][:-5],
                         'Mon, 01 Aug 2005 07:49:23 ')
        del message['x-mailman-approved-at']
        # The Message-ID matches the original.
        self.assertEqual(message['message-id'], '<alpha>')
        # Anne sent the message and the mailing list received it.
        self.assertEqual(message['from'], 'anne@example.com')
        self.assertEqual(message['to'], 'test@example.com')
        # The Subject header has the list's prefix.
        self.assertEqual(message['subject'], '[Test] hold me')
        # The list's -bounce address is the actual sender, and Bart is the
        # only actual recipient.  These headers are added by the testing
        # framework and don't show up in production.  They match the RFC 5321
        # envelope.
        self.assertEqual(message['x-mailfrom'], 'test-bounces@example.com')
        self.assertEqual(message['x-rcptto'], 'bart@example.com')

    def test_hold_action_alias_for_defer(self):
        # In handle_message(), the 'hold' action is the same as 'defer' for
        # purposes of this API.
        request_id = hold_message(self._mlist, self._msg)
        handle_message(self._mlist, request_id, Action.defer)
        # The message is still in the pending requests.
        requests_db = IListRequests(self._mlist)
        key, data = requests_db.get_request(request_id)
        self.assertEqual(key, '<alpha>')
        handle_message(self._mlist, request_id, Action.hold)
        key, data = requests_db.get_request(request_id)
        self.assertEqual(key, '<alpha>')
