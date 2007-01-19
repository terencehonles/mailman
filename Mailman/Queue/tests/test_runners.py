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

"""Unit tests for the various Mailman qrunner modules."""

import os
import email
import shutil
import tempfile
import unittest

from Mailman.Message import Message
from Mailman.Queue.NewsRunner import prepare_message
from Mailman.Queue.Runner import Runner
from Mailman.Queue.Switchboard import Switchboard
from Mailman.testing.base import TestBase



class TestPrepMessage(TestBase):
    def test_remove_unacceptables(self):
        eq = self.assertEqual
        msg = email.message_from_string("""\
From: aperson@dom.ain
To: _xtest@dom.ain
NNTP-Posting-Host: news.dom.ain
NNTP-Posting-Date: today
X-Trace: blah blah
X-Complaints-To: abuse@dom.ain
Xref: blah blah
Xref: blah blah
Date-Received: yesterday
Posted: tomorrow
Posting-Version: 99.99
Relay-Version: 88.88
Received: blah blah

A message
""")
        msgdata = {}
        prepare_message(self._mlist, msg, msgdata)
        eq(msgdata.get('prepped'), 1)
        eq(msg['from'], 'aperson@dom.ain')
        eq(msg['to'], '_xtest@dom.ain')
        eq(msg['nntp-posting-host'], None)
        eq(msg['nntp-posting-date'], None)
        eq(msg['x-trace'], None)
        eq(msg['x-complaints-to'], None)
        eq(msg['xref'], None)
        eq(msg['date-received'], None)
        eq(msg['posted'], None)
        eq(msg['posting-version'], None)
        eq(msg['relay-version'], None)
        eq(msg['received'], None)

    def test_munge_duplicates_no_duplicates(self):
        eq = self.assertEqual
        msg = email.message_from_string("""\
From: aperson@dom.ain
To: _xtest@dom.ain
Cc: someother@dom.ain
Content-Transfer-Encoding: yes

A message
""")
        msgdata = {}
        prepare_message(self._mlist, msg, msgdata)
        eq(msgdata.get('prepped'), 1)
        eq(msg['from'], 'aperson@dom.ain')
        eq(msg['to'], '_xtest@dom.ain')
        eq(msg['cc'], 'someother@dom.ain')
        eq(msg['content-transfer-encoding'], 'yes')

    def test_munge_duplicates(self):
        eq = self.assertEqual
        msg = email.message_from_string("""\
From: aperson@dom.ain
To: _xtest@dom.ain
To: two@dom.ain
Cc: three@dom.ain
Cc: four@dom.ain
Cc: five@dom.ain
Content-Transfer-Encoding: yes
Content-Transfer-Encoding: no
Content-Transfer-Encoding: maybe

A message
""")
        msgdata = {}
        prepare_message(self._mlist, msg, msgdata)
        eq(msgdata.get('prepped'), 1)
        eq(msg.get_all('from'), ['aperson@dom.ain'])
        eq(msg.get_all('to'), ['_xtest@dom.ain'])
        eq(msg.get_all('cc'), ['three@dom.ain'])
        eq(msg.get_all('content-transfer-encoding'), ['yes'])
        eq(msg.get_all('x-original-to'), ['two@dom.ain'])
        eq(msg.get_all('x-original-cc'), ['four@dom.ain', 'five@dom.ain'])
        eq(msg.get_all('x-original-content-transfer-encoding'),
           ['no', 'maybe'])



class TestSwitchboard(TestBase):
    def setUp(self):
        TestBase.setUp(self)
        self._tmpdir = tempfile.mkdtemp()
        self._msg = email.message_from_string("""\
From: aperson@dom.ain
To: _xtest@dom.ain

A test message.
""")
        self._sb = Switchboard(self._tmpdir)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, True)
        TestBase.tearDown(self)

    def _count_qfiles(self):
        files = {}
        for qfile in os.listdir(self._tmpdir):
            root, ext = os.path.splitext(qfile)
            files[ext] = files.get(ext, 0) + 1
        return files

    def test_whichq(self):
        self.assertEqual(self._sb.whichq(), self._tmpdir)

    def test_enqueue(self):
        eq = self.assertEqual
        self._sb.enqueue(self._msg, listname='_xtest@dom.ain')
        files = self._count_qfiles()
        eq(len(files), 1)
        eq(files['.pck'], 1)

    def test_dequeue(self):
        eq = self.assertEqual
        self._sb.enqueue(self._msg, listname='_xtest@dom.ain', foo='yes')
        count = 0
        for filebase in self._sb.files():
            msg, data = self._sb.dequeue(filebase)
            self._sb.finish(filebase)
            count += 1
            eq(msg['from'], self._msg['from'])
            eq(msg['to'], self._msg['to'])
            eq(data['foo'], 'yes')
        eq(count, 1)
        files = self._count_qfiles()
        eq(len(files), 0)

    def test_bakfile(self):
        eq = self.assertEqual
        self._sb.enqueue(self._msg, listname='_xtest@dom.ain')
        self._sb.enqueue(self._msg, listname='_xtest@dom.ain')
        self._sb.enqueue(self._msg, listname='_xtest@dom.ain')
        for filebase in self._sb.files():
            self._sb.dequeue(filebase)
        files = self._count_qfiles()
        eq(len(files), 1)
        eq(files['.bak'], 3)

    def test_recover(self):
        eq = self.assertEqual
        self._sb.enqueue(self._msg, listname='_xtest@dom.ain')
        for filebase in self._sb.files():
            self._sb.dequeue(filebase)
            # Not calling sb.finish() leaves .bak files
        sb2 = Switchboard(self._tmpdir, recover=True)
        files = self._count_qfiles()
        eq(len(files), 1)
        eq(files['.pck'], 1)



class TestableRunner(Runner):
    def _dispose(self, mlist, msg, msgdata):
        self.msg = msg
        self.data = msgdata
        return False

    def _doperiodic(self):
        self.stop()

    def _snooze(self, filecnt):
        return


class TestRunner(TestBase):
    def setUp(self):
        TestBase.setUp(self)
        self._tmpdir = tempfile.mkdtemp()
        self._msg = email.message_from_string("""\
From: aperson@dom.ain
To: _xtest@dom.ain

A test message.
""", Message)
        class MyRunner(TestableRunner):
            QDIR = self._tmpdir
        self._runner = MyRunner()

    def tearDown(self):
        shutil.rmtree(self._tmpdir, True)
        TestBase.tearDown(self)

    def test_run_loop(self):
        eq = self.assertEqual
        sb = Switchboard(self._tmpdir)
        sb.enqueue(self._msg, listname='_xtest@example.com', foo='yes')
        self._runner.run()
        eq(self._runner.msg['from'], self._msg['from'])
        eq(self._runner.msg['to'], self._msg['to'])
        eq(self._runner.data['foo'], 'yes')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestPrepMessage))
    suite.addTest(unittest.makeSuite(TestSwitchboard))
    suite.addTest(unittest.makeSuite(TestRunner))
    return suite
