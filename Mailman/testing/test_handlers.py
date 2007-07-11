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

"""Unit tests for the various Mailman/Handlers/*.py modules."""

import os
import sha
import time
import email
import errno
import cPickle
import unittest

from email.Generator import Generator

from Mailman import Errors
from Mailman import Message
from Mailman import Version
from Mailman import passwords
from Mailman.MailList import MailList
from Mailman.Queue.Switchboard import Switchboard
from Mailman.configuration import config
from Mailman.testing.base import TestBase

from Mailman.Handlers import Acknowledge
from Mailman.Handlers import AfterDelivery
from Mailman.Handlers import Approve
from Mailman.Handlers import Moderate
from Mailman.Handlers import Scrubber
# Don't test handlers such as SMTPDirect and Sendmail here



def password(cleartext):
    return passwords.make_secret(cleartext, passwords.Schemes.ssha)



class TestApprove(TestBase):
    def test_short_circuit(self):
        msgdata = {'approved': 1}
        rtn = Approve.process(self._mlist, None, msgdata)
        # Not really a great test, but there's little else to assert
        self.assertEqual(rtn, None)

    def test_approved_moderator(self):
        mlist = self._mlist
        mlist.mod_password = password('wazoo')
        msg = email.message_from_string("""\
Approved: wazoo

""")
        msgdata = {}
        Approve.process(mlist, msg, msgdata)
        self.failUnless(msgdata.has_key('approved'))
        self.assertEqual(msgdata['approved'], 1)

    def test_approve_moderator(self):
        mlist = self._mlist
        mlist.mod_password = password('wazoo')
        msg = email.message_from_string("""\
Approve: wazoo

""")
        msgdata = {}
        Approve.process(mlist, msg, msgdata)
        self.failUnless(msgdata.has_key('approved'))
        self.assertEqual(msgdata['approved'], 1)

    def test_approved_admin(self):
        mlist = self._mlist
        mlist.password = password('wazoo')
        msg = email.message_from_string("""\
Approved: wazoo

""")
        msgdata = {}
        Approve.process(mlist, msg, msgdata)
        self.failUnless(msgdata.has_key('approved'))
        self.assertEqual(msgdata['approved'], 1)

    def test_approve_admin(self):
        mlist = self._mlist
        mlist.password = password('wazoo')
        msg = email.message_from_string("""\
Approve: wazoo

""")
        msgdata = {}
        Approve.process(mlist, msg, msgdata)
        self.failUnless(msgdata.has_key('approved'))
        self.assertEqual(msgdata['approved'], 1)

    def test_unapproved(self):
        mlist = self._mlist
        mlist.password = password('zoowa')
        msg = email.message_from_string("""\
Approve: wazoo

""")
        msgdata = {}
        Approve.process(mlist, msg, msgdata)
        self.assertEqual(msgdata.get('approved'), None)

    def test_trip_beentheres(self):
        mlist = self._mlist
        msg = email.message_from_string("""\
X-BeenThere: %s

""" % mlist.GetListEmail())
        self.assertRaises(Errors.LoopError, Approve.process, mlist, msg, {})



class TestScrubber(TestBase):
    def test_save_attachment(self):
        mlist = self._mlist
        msg = email.message_from_string("""\
Content-Type: image/gif; name="xtest.gif"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="xtest.gif"

R0lGODdhAQABAIAAAAAAAAAAACwAAAAAAQABAAACAQUAOw==
""")
        Scrubber.save_attachment(mlist, msg, '')
        f = open(os.path.join(mlist.archive_dir(), 'attachment.gif'))
        img = f.read()
        self.assertEqual(img.startswith('GIF87a'), True)
        self.assertEqual(len(img), 34)

    def _saved_file(self, s):
        # a convenient function to get the saved attachment file
        for i in s.splitlines():
            if i.startswith('URL: '):
                f = i.replace(
                      'URL: <' + self._mlist.GetBaseArchiveURL() + '/' , '')
        f = os.path.join(self._mlist.archive_dir(), f.rstrip('>'))
        return f

    def test_scrub_image(self):
        mlist = self._mlist
        msg = email.message_from_string("""\
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="BOUNDARY"

--BOUNDARY
Content-type: text/plain; charset=us-ascii

This is a message.
--BOUNDARY
Content-Type: image/gif; name="xtest.gif"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="xtest.gif"

R0lGODdhAQABAIAAAAAAAAAAACwAAAAAAQABAAACAQUAOw==
--BOUNDARY--
""")
        Scrubber.process(mlist, msg, {})
        # saved file
        img = open(self._saved_file(msg.get_payload())).read()
        self.assertEqual(img.startswith('GIF87a'), True)
        self.assertEqual(len(img), 34)
        # scrubbed message
        s = '\n'.join([l for l in msg.get_payload().splitlines()
                               if not l.startswith('URL: ')])
        self.assertEqual(s, """\
This is a message.
-------------- next part --------------
A non-text attachment was scrubbed...
Name: xtest.gif
Type: image/gif
Size: 34 bytes
Desc: not available""")

    def test_scrub_text(self):
        mlist = self._mlist
        msg = email.message_from_string("""\
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary="BOUNDARY"

--BOUNDARY
Content-type: text/plain; charset=us-ascii; format=flowed; delsp=no

This is a message.
--BOUNDARY
Content-type: text/plain; name="xtext.txt"
Content-Disposition: attachment; filename="xtext.txt"

This is a text attachment.
--BOUNDARY--
""")
        Scrubber.process(mlist, msg, {})
        self.assertEqual(msg.get_param('format'), 'flowed')
        self.assertEqual(msg.get_param('delsp'), 'no')
        txt = open(self._saved_file(msg.get_payload())).read()
        self.assertEqual(txt, 'This is a text attachment.')
        s = '\n'.join([l for l in msg.get_payload().splitlines()
                               if not l.startswith('URL: ')])
        self.assertEqual(s, """\
This is a message.
-------------- next part --------------
An embedded and charset-unspecified text was scrubbed...
Name: xtext.txt""")



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApprove))
    suite.addTest(unittest.makeSuite(TestScrubber))
    return suite
