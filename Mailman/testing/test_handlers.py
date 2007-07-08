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
from Mailman.Handlers import ToArchive
from Mailman.Handlers import ToDigest



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



class TestToArchive(TestBase):
    def setUp(self):
        TestBase.setUp(self)
        # We're going to want to inspect this queue directory
        self._sb = Switchboard(config.ARCHQUEUE_DIR)

    def tearDown(self):
        for f in os.listdir(config.ARCHQUEUE_DIR):
            os.unlink(os.path.join(config.ARCHQUEUE_DIR, f))
        TestBase.tearDown(self)

    def test_short_circuit(self):
        eq = self.assertEqual
        msgdata = {'isdigest': 1}
        ToArchive.process(self._mlist, None, msgdata)
        eq(len(self._sb.files()), 0)
        # Try the other half of the or...
        self._mlist.archive = 0
        ToArchive.process(self._mlist, None, msgdata)
        eq(len(self._sb.files()), 0)
        # Now try the various message header shortcuts
        msg = email.message_from_string("""\
X-No-Archive: YES

""")
        self._mlist.archive = 1
        ToArchive.process(self._mlist, msg, {})
        eq(len(self._sb.files()), 0)
        # And for backwards compatibility
        msg = email.message_from_string("""\
X-Archive: NO

""")
        ToArchive.process(self._mlist, msg, {})
        eq(len(self._sb.files()), 0)

    def test_normal_archiving(self):
        eq = self.assertEqual
        msg = email.message_from_string("""\
Subject: About Mailman

It rocks!
""")
        ToArchive.process(self._mlist, msg, {})
        files = self._sb.files()
        eq(len(files), 1)
        msg2, data = self._sb.dequeue(files[0])
        eq(len(data), 3)
        eq(data['version'], 3)
        # Clock skew makes this unreliable
        #self.failUnless(data['received_time'] <= time.time())
        eq(msg.as_string(unixfrom=0), msg2.as_string(unixfrom=0))



class TestToDigest(TestBase):
    def _makemsg(self, i=0):
        msg = email.message_from_string("""From: aperson@example.org
To: _xtest@example.com
Subject: message number %(i)d

Here is message %(i)d
""" % {'i' : i})
        return msg

    def setUp(self):
        TestBase.setUp(self)
        self._path = os.path.join(self._mlist.fullpath(), 'digest.mbox')
        fp = open(self._path, 'w')
        g = Generator(fp)
        for i in range(5):
            g.flatten(self._makemsg(i), unixfrom=1)
        fp.close()
        self._sb = Switchboard(config.VIRGINQUEUE_DIR)

    def tearDown(self):
        try:
            os.unlink(self._path)
        except OSError, e:
            if e.errno <> errno.ENOENT: raise
        for f in os.listdir(config.VIRGINQUEUE_DIR):
            os.unlink(os.path.join(config.VIRGINQUEUE_DIR, f))
        TestBase.tearDown(self)

    def test_short_circuit(self):
        eq = self.assertEqual
        mlist = self._mlist
        mlist.digestable = 0
        eq(ToDigest.process(mlist, None, {}), None)
        mlist.digestable = 1
        eq(ToDigest.process(mlist, None, {'isdigest': 1}), None)
        eq(self._sb.files(), [])

    def test_undersized(self):
        msg = self._makemsg(99)
        size = os.path.getsize(self._path) + len(str(msg))
        self._mlist.digest_size_threshhold = (size + 1) * 1024
        ToDigest.process(self._mlist, msg, {})
        self.assertEqual(self._sb.files(), [])

    def test_send_a_digest(self):
        eq = self.assertEqual
        mlist = self._mlist
        msg = self._makemsg(99)
        size = os.path.getsize(self._path) + len(str(msg))
        mlist.digest_size_threshhold = 0
        ToDigest.process(mlist, msg, {})
        files = self._sb.files()
        # There should be two files in the queue, one for the MIME digest and
        # one for the RFC 1153 digest.
        eq(len(files), 2)
        # Now figure out which of the two files is the MIME digest and which
        # is the RFC 1153 digest.
        for filebase in files:
            qmsg, qdata = self._sb.dequeue(filebase)
            if qmsg.get_content_maintype() == 'multipart':
                mimemsg = qmsg
                mimedata = qdata
            else:
                rfc1153msg = qmsg
                rfc1153data = qdata
        eq(rfc1153msg.get_content_type(), 'text/plain')
        eq(mimemsg.get_content_type(), 'multipart/mixed')
        eq(mimemsg['from'], mlist.GetRequestEmail())
        eq(mimemsg['subject'],
           '%(realname)s Digest, Vol %(volume)d, Issue %(issue)d' % {
            'realname': mlist.real_name,
            'volume'  : mlist.volume,
            'issue'   : mlist.next_digest_number - 1,
            })
        eq(mimemsg['to'], mlist.GetListEmail())
        # BAW: this test is incomplete...

    def test_send_i18n_digest(self):
        eq = self.assertEqual
        mlist = self._mlist
        mlist.preferred_language = 'fr'
        msg = email.message_from_string("""\
From: aperson@example.org
To: _xtest@example.com
Subject: =?iso-2022-jp?b?GyRCMGxIVhsoQg==?=
MIME-Version: 1.0
Content-Type: text/plain; charset=iso-2022-jp
Content-Transfer-Encoding: 7bit

\x1b$B0lHV\x1b(B
""")
        mlist.digest_size_threshhold = 0
        ToDigest.process(mlist, msg, {})
        files = self._sb.files()
        eq(len(files), 2)
        for filebase in files:
            qmsg, qdata = self._sb.dequeue(filebase)
            if qmsg.get_content_maintype() == 'multipart':
                mimemsg = qmsg
                mimedata = qdata
            else:
                rfc1153msg = qmsg
                rfc1153data = qdata
        eq(rfc1153msg.get_content_type(), 'text/plain')
        eq(rfc1153msg.get_content_charset(), 'utf-8')
        eq(rfc1153msg['content-transfer-encoding'], 'base64')
        toc = mimemsg.get_payload()[1]
        eq(toc.get_content_type(), 'text/plain')
        eq(toc.get_content_charset(), 'utf-8')
        eq(toc['content-transfer-encoding'], 'base64')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestApprove))
    suite.addTest(unittest.makeSuite(TestScrubber))
    suite.addTest(unittest.makeSuite(TestToArchive))
    suite.addTest(unittest.makeSuite(TestToDigest))
    return suite
