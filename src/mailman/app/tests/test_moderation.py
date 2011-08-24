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

"""Moderation tests."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.app.moderator import handle_message, hold_message
from mailman.interfaces.action import Action
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
        # Python 2.7 has assertMultiLineEqual
        self.maxDiff = None
        self.eq = getattr(self, 'assertMultiLineEqual',
                          getattr(self, 'assertEqual'))

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
        # Delete variable headers which can't be compared.
        self.assertTrue('x-mailman-version' in message)
        del message['x-mailman-version']
        self.assertTrue('x-peer' in message)
        del message['x-peer']
        # The X-Mailman-Approved-At header has local timezone information in
        # it, so test that separately.
        self.assertEqual(message['x-mailman-approved-at'][:-4],
                         'Mon, 01 Aug 2005 07:49:23 -')
        del message['x-mailman-approved-at']
        self.eq(message.as_string(), """\
From: anne@example.com
To: test@example.com
Message-ID: <alpha>
Subject: [Test] hold me
X-BeenThere: test@example.com
Precedence: list
List-Id: <test.example.com>
X-Message-ID-Hash: XZ3DGG4V37BZTTLXNUX4NABB4DNQHTCP
List-Post: <mailto:test@example.com>
List-Subscribe: <http://lists.example.com/listinfo/test@example.com>,
 <mailto:test-join@example.com>
Archived-At: http://lists.example.com/archives/XZ3DGG4V37BZTTLXNUX4NABB4DNQHTCP
List-Unsubscribe: <http://lists.example.com/listinfo/test@example.com>,
 <mailto:test-leave@example.com>
List-Archive: <http://lists.example.com/archives/test@example.com>
List-Help: <mailto:test-request@example.com?subject=help>
X-MailFrom: test-bounces@example.com
X-RcptTo: bart@example.com

""")        



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestModeration))
    return suite
