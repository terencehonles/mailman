# Copyright (C) 2001-2006 by the Free Software Foundation, Inc.
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

"""Base class for tests that email things."""

import os
import time
import errno
import smtpd
import socket
import asyncore
import subprocess

from Mailman.configuration import config
from Mailman.testing.base import TestBase

TESTPORT = 10825



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
    def _configure(self, fp):
        TestBase._configure(self, fp)
        print >> fp, 'SMTPPORT =', TESTPORT
        config.SMTPPORT = TESTPORT

    def setUp(self):
        TestBase.setUp(self)
        # Second argument is ignored.
        self._server = SinkServer(('localhost', TESTPORT), None)
        try:
            os.system('bin/mailmanctl -C %s -q start' % self._config)
            # If any errors occur in the above, be sure to manually call
            # tearDown().  unittest doesn't call tearDown() for errors in
            # setUp().
        except:
            self.tearDown()

    def tearDown(self):
        os.system('bin/mailmanctl -C %s -q stop' % self._config)
        self._server.close()
        # Wait a while until the server actually goes away
        while True:
            try:
                s = socket.socket()
                s.connect(('localhost', TESTPORT))
                s.close()
                time.sleep(3)
            except socket.error, e:
                # IWBNI e had an errno attribute
                if e[0] == errno.ECONNREFUSED:
                    break
                else:
                    raise
        TestBase.tearDown(self)

    def _readmsg(self):
        global MSGTEXT
        # Save and unlock the list so that the qrunner process can open it and
        # lock it if necessary.  We'll re-lock the list in our finally clause
        # since that if an invariant of the test harness.
        self._mlist.Unlock()
        try:
            try:
                # timeout is in milliseconds, see asyncore.py poll3()
                asyncore.loop()
                MSGTEXT = None
            except asyncore.ExitNow:
                pass
            return MSGTEXT
        finally:
            self._mlist.Lock()
