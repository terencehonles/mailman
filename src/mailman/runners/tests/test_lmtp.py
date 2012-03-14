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

"""Tests for the LMTP server."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestLMTP',
    ]


import smtplib
import unittest

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.testing.helpers import get_lmtp_client, get_queue_messages
from mailman.testing.layers import LMTPLayer



class TestLMTP(unittest.TestCase):
    """Test various aspects of the LMTP server."""

    layer = LMTPLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        config.db.commit()
        self._lmtp = get_lmtp_client(quiet=True)
        self._lmtp.lhlo('remote.example.org')

    def tearDown(self):
        self._lmtp.close()

    def test_message_id_required(self):
        # The message is rejected if it does not have a Message-ID header.
        try:
            self._lmtp.sendmail('anne@example.com', ['test@example.com'], """\
From: anne@example.com
To: test@example.com
Subject: This has no Message-ID header

""")
        except smtplib.SMTPDataError as error:
            pass
        else:
            raise AssertionError('SMTPDataError expected')
        # LMTP returns a 550: Requested action not taken: mailbox unavailable
        # (e.g., mailbox not found, no access, or command rejected for policy
        # reasons)
        self.assertEqual(error.smtp_code, 550)
        self.assertEqual(error.smtp_error, 'No Message-ID header provided')

    def test_message_id_hash_is_added(self):
        self._lmtp.sendmail('anne@example.com', ['test@example.com'], """\
From: anne@example.com
To: test@example.com
Message-ID: <ant>
Subject: This has a Message-ID but no X-Message-ID-Hash

""")
        messages = get_queue_messages('in')
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].msg['x-message-id-hash'],
                         'MS6QLWERIJLGCRF44J7USBFDELMNT2BW')

    def test_original_message_id_hash_is_overwritten(self):
        self._lmtp.sendmail('anne@example.com', ['test@example.com'], """\
From: anne@example.com
To: test@example.com
Message-ID: <ant>
X-Message-ID-Hash: IGNOREME
Subject: This has a Message-ID but no X-Message-ID-Hash

""")
        messages = get_queue_messages('in')
        self.assertEqual(len(messages), 1)
        all_headers = messages[0].msg.get_all('x-message-id-hash')
        self.assertEqual(len(all_headers), 1)
        self.assertEqual(messages[0].msg['x-message-id-hash'],
                         'MS6QLWERIJLGCRF44J7USBFDELMNT2BW')
