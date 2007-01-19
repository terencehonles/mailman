# Copyright (C) 2001-2007 by the Free Software Foundation, Inc.
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

"""Unit tests for the various Message class methods."""

import email
import unittest

from Mailman import Errors
from Mailman import Message
from Mailman import Version
from Mailman.testing.emailbase import EmailBase



class TestSentMessage(EmailBase):
    def test_user_notification(self):
        eq = self.assertEqual
        unless = self.failUnless
        msg = Message.UserNotification(
            'aperson@example.org',
            '_xtest@example.com',
            'Your Test List',
            'About your test list')
        msg.send(self._mlist)
        qmsg = email.message_from_string(self._readmsg())
        eq(qmsg['subject'], 'Your Test List')
        eq(qmsg['from'], '_xtest@example.com')
        eq(qmsg['to'], 'aperson@example.org')
        # The Message-ID: header has some time-variant information
        msgid = qmsg['message-id']
        unless(msgid.startswith('<mailman.'))
        unless(msgid.endswith('._xtest@example.com>'))
        eq(qmsg['sender'], '_xtest-bounces@example.com')
        eq(qmsg['errors-to'], '_xtest-bounces@example.com')
        eq(qmsg['x-beenthere'], '_xtest@example.com')
        eq(qmsg['x-mailman-version'], Version.VERSION)
        eq(qmsg['precedence'], 'bulk')
        # UserNotifications have reduced_list_headers so it won't have
        # List-Help, List-Subscribe, or List-Unsubscribe.  XXX Why would that
        # possibly be?
        eq(qmsg['list-help'],
           '<mailto:_xtest-request@example.com?subject=help>')
        eq(qmsg['list-subscribe'], """\
<http://www.example.com/mailman/listinfo/_xtest@example.com>, 
\t<mailto:_xtest-request@example.com?subject=subscribe>""")
        eq(qmsg['list-id'], '<_xtest.example.com>')
        eq(qmsg['list-unsubscribe'], """\
<http://www.example.com/mailman/listinfo/_xtest@example.com>, 
\t<mailto:_xtest-request@example.com?subject=unsubscribe>""")
        eq(qmsg.get_payload(), 'About your test list')

    def test_bounce_message(self):
        eq = self.assertEqual
        unless = self.failUnless
        msg = email.message_from_string("""\
To: _xtest@example.com
From: nobody@example.com
Subject: and another thing

yadda yadda yadda
""", Message.Message)
        self._mlist.BounceMessage(msg, {})
        qmsg = email.message_from_string(self._readmsg())
        unless(qmsg.is_multipart())
        eq(len(qmsg.get_payload()), 2)
        # The first payload is the details of the bounce action, and the
        # second message is the message/rfc822 attachment of the original
        # message.
        msg1 = qmsg.get_payload(0)
        eq(msg1.get_content_type(), 'text/plain')
        eq(msg1.get_payload(), '[No bounce details are available]')
        msg2 = qmsg.get_payload(1)
        eq(msg2.get_content_type(), 'message/rfc822')
        unless(msg2.is_multipart())
        msg3 = msg2.get_payload(0)
        eq(msg3.get_payload(), 'yadda yadda yadda\n')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSentMessage))
    return suite
