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
import stat
import smtpd
import socket
import asyncore
import tempfile
import subprocess

from Mailman.configuration import config
from Mailman.testing.base import TestBase

TESTPORT    = 10825
PERMISSIONS = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH



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
        # Find an unused non-root requiring port to listen on.  Set up a
        # configuration file that causes the underlying outgoing runner to use
        # the same port, then start Mailman.
        fd, self._configfile = tempfile.mkstemp(suffix='.cfg')
        fp = os.fdopen(fd, 'w')
        print >> fp, 'SMTPPORT =', TESTPORT
        config.SMTPPORT = TESTPORT
        fp.close()
        # Loosen up the permissions
        os.chmod(self._configfile, PERMISSIONS)
        # Second argument is ignored.
        self._server = SinkServer(('localhost', TESTPORT), None)
        os.system('bin/mailmanctl -C %s -q start' % self._configfile)
        # Don't call our superclass's setUp until the above succeeds,
        # otherwise, should it fail, we'll be left with a stale _xtest list
        # which would have to be manually removed.  unittest doesn't call
        # tearDown() for errors in setUp().
        TestBase.setUp(self)

    def tearDown(self):
        os.system('bin/mailmanctl -C %s -q stop' % self._configfile)
        self._server.close()
        TestBase.tearDown(self)
        os.remove(self._configfile)

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
