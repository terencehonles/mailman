# Copyright (C) 2001 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Base class for test that email things.
"""

import asyncore
import unittest
import smtpd
import email

from Mailman import mm_cfg
from Mailman import Message
from Mailman import Version

from TestBase import TestBase

# You may have to change this if there is already something running on port
# 8025, or you aren't allowed to create sockets reading this port on
# localhost.
SMTPPORT = 8025



MSGTEXT = None

class OneShotChannel(smtpd.SMTPChannel):
    def smtp_QUIT(self, arg):
        smtpd.SMTPChannel.smtp_QUIT(self, arg)
        raise asyncore.ExitNow


class SinkServer(smtpd.SMTPServer):
    def handle_accept(self):
        conn, addr = self.accept()
        channel = OneShotChannel(self, conn, addr)

    def process_message(self, peer, mailfrom, rcpttos, data):
        global MSGTEXT
        MSGTEXT = data



class EmailBase(TestBase):
    def setUp(self):
        TestBase.setUp(self)
        # Second argument tuple is ignored.
        self._server = SinkServer(('localhost', SMTPPORT), ('localhost', 25))
        # Change the globals so the runner will contact the server above
        mm_cfg.SMTPHOST = 'localhost'
        mm_cfg.SMTPPORT = SMTPPORT

    def _readmsg(self):
        global MSGTEXT
        # Save and unlock the list so that the qrunner process can open it and
        # lock it if necessary.  We'll re-lock the list in our finally clause
        # since that if an invariant of the test harness.
        self._mlist.Unlock()
        try:
            try:
                # timeout is in milliseconds, see asyncore.py poll3()
                asyncore.loop(timeout=30.0)
                MSGTEXT = None
            except asyncore.ExitNow:
                pass
            return MSGTEXT
        finally:
            self._mlist.Lock()



class TestUserNotification(unittest.TestCase, EmailBase):
    def setUp(self):
        unittest.TestCase.setUp(self)
        EmailBase.setUp(self)

    def tearDown(self):
        EmailBase.tearDown(self)
        unittest.TestCase.tearDown(self)

    def test_user_notification(self):
        eq = self.assertEqual
        unless = self.failUnless
        msg = Message.UserNotification(
            'aperson@dom.ain',
            '_xtest@dom.ain',
            'Your Test List',
            'About your test list')
        msg.send(self._mlist)
        text = self._readmsg()
        qmsg = email.message_from_string(text)
        eq(qmsg['subject'], 'Your Test List')
        eq(qmsg['from'], '_xtest@dom.ain')
        eq(qmsg['to'], 'aperson@dom.ain')
        # The Message-ID: header has some time-variant information
        msgid = qmsg['message-id']
        unless(msgid.startswith('<mailman.'))
        unless(msgid.endswith('._xtest@dom.ain>'))
        eq(qmsg['sender'], '_xtest-admin@dom.ain')
        eq(qmsg['errors-to'], '_xtest-admin@dom.ain')
        eq(qmsg['x-beenthere'], '_xtest@dom.ain')
        eq(qmsg['x-mailman-version'], Version.VERSION)
        eq(qmsg['precedence'], 'bulk')
        eq(qmsg['list-help'], '<mailto:_xtest-request@dom.ain?subject=help>')
        eq(qmsg['list-post'], '<mailto:_xtest@dom.ain>')
        eq(qmsg['list-subscribe'], """\
<http://www.dom.ain/mailman/listinfo/_xtest>,
	<mailto:_xtest-request@dom.ain?subject=subscribe>""")
        eq(qmsg['list-id'], '<_xtest.dom.ain>')
        eq(qmsg['list-unsubscribe'], """\
<http://www.dom.ain/mailman/listinfo/_xtest>,
	<mailto:_xtest-request@dom.ain?subject=unsubscribe>""")
        eq(qmsg['list-archive'], '<http://www.dom.ain/pipermail/_xtest/>')
        eq(qmsg.get_payload(), 'About your test list')



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestUserNotification))
    return suite



if __name__ == '__main__':
    unittest.main(defaultTest='suite')
