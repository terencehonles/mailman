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

"""Test mailing list joins."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from email.iterators import body_line_iterator

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.runners.command import CommandRunner
from mailman.testing.helpers import (
    get_queue_messages,
    make_testable_runner,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestJoin(unittest.TestCase):
    """Test mailing list joins."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._commandq = config.switchboards['command']
        self._runner = make_testable_runner(CommandRunner, 'command')

    def test_double_confirmation(self):
        # A join request comes in using both the -join address and the word
        # 'subscribe' in the first line of the body.  This should produce just
        # one subscription request and one confirmation response.
        msg = mfs("""\
From: anne@example.org
To: test-join@example.com

subscribe
""")
        # Adding the subaddress to the metadata dictionary mimics what happens
        # when the above email message is first processed by the lmtp runner.
        # For convenience, we skip that step in this test.
        self._commandq.enqueue(msg, dict(listname='test@example.com',
                                         subaddress='join'))
        self._runner.run()
        # There will be two messages in the queue.  The first one is a reply
        # to Anne notifying her of the status of her command email.  The
        # second one is the confirmation message of her join request.
        messages = get_queue_messages('virgin', sort_on='subject')
        self.assertEqual(len(messages), 2)
        # 'The' comes before 'confirm'
        self.assertTrue(str(messages[0].msg['subject']).startswith('confirm'))
        self.assertEqual(messages[1].msg['subject'],
                         'The results of your email commands')
        # Search the contents of the results message.  There should be just
        # one 'Confirmation email' line.
        confirmation_lines = []
        in_results = False
        for line in body_line_iterator(messages[1].msg, decode=True):
            line = line.strip()
            if in_results:
                if line.startswith('- Done'):
                    break
                if len(line) > 0:
                    confirmation_lines.append(line)
            if line.strip() == '- Results:':
                in_results = True
        # There should be exactly one confirmation line.
        self.assertEqual(len(confirmation_lines), 1)
        # And the confirmation line should name Anne's email address.
        self.assertTrue('anne@example.org' in confirmation_lines[0])
