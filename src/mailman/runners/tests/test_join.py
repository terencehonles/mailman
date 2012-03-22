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
    'TestJoin',
    'TestJoinWithDigests',
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.member import DeliveryMode
from mailman.interfaces.registrar import IRegistrar
from mailman.interfaces.subscriptions import ISubscriptionService
from mailman.interfaces.usermanager import IUserManager
from mailman.runners.command import CommandRunner
from mailman.testing.helpers import (
    body_line_iterator,
    get_queue_messages,
    make_testable_runner,
    reset_the_world,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestJoin(unittest.TestCase):
    """Test mailing list joins."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._commandq = config.switchboards['command']
        self._runner = make_testable_runner(CommandRunner, 'command')

    def tearDown(self):
        reset_the_world()

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
        self.assertTrue(str(messages[1].msg['subject']).startswith('confirm'))
        self.assertEqual(messages[0].msg['subject'],
                         'The results of your email commands')
        # Search the contents of the results message.  There should be just
        # one 'Confirmation email' line.
        confirmation_lines = []
        in_results = False
        for line in body_line_iterator(messages[0].msg, decode=True):
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

    def test_join_when_already_a_member(self):
        anne = getUtility(IUserManager).create_user('anne@example.org')
        self._mlist.subscribe(list(anne.addresses)[0])
        # When someone tries to join by email and they are already a member,
        # ignore the request.
        msg = mfs("""\
From: anne@example.org
To: test-join@example.com
Subject: join

""")
        self._commandq.enqueue(msg, dict(listname='test@example.com'))
        self._runner.run()
        # There will be one message in the queue - a reply to Anne notifying
        # her of the status of her command email.  Because Anne is already
        # subscribed to the list, she gets and needs no confirmation.
        messages = get_queue_messages('virgin')
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].msg['subject'],
                         'The results of your email commands')
        # Search the contents of the results message.  There should be just
        # one 'Confirmation email' line.
        confirmation_lines = []
        in_results = False
        for line in body_line_iterator(messages[0].msg, decode=True):
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



class TestJoinWithDigests(unittest.TestCase):
    """Test mailing list joins with the digests=<no|mime|plain> argument."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._commandq = config.switchboards['command']
        self._runner = make_testable_runner(CommandRunner, 'command')

    def tearDown(self):
        reset_the_world()

    def _confirm(self):
        # There will be two messages in the queue - the confirmation messages,
        # and a reply to Anne notifying her of the status of her command
        # email.  We need to dig the confirmation token out of the Subject
        # header of the latter so that we can confirm the subscription.
        messages = get_queue_messages('virgin', sort_on='subject')
        self.assertEqual(len(messages), 2)
        subject_words = str(messages[1].msg['subject']).split()
        self.assertEqual(subject_words[0], 'confirm')
        token = subject_words[1]
        status = getUtility(IRegistrar).confirm(token)
        self.assertTrue(status, 'Confirmation failed')
        # Now, make sure that Anne is a member of the list and is receiving
        # digest deliveries.
        members = getUtility(ISubscriptionService).find_members(
            'anne@example.org')
        self.assertEqual(len(members), 1)
        return members[0]

    def test_join_with_implicit_no_digests(self):
        # Test the digest=mime argument to the join command.
        msg = mfs("""\
From: anne@example.org
To: test-request@example.com

join
""")
        self._commandq.enqueue(msg, dict(listname='test@example.com'))
        self._runner.run()
        anne = self._confirm()
        self.assertEqual(anne.address.email, 'anne@example.org')
        self.assertEqual(anne.delivery_mode, DeliveryMode.regular)

    def test_join_with_explicit_no_digests(self):
        # Test the digest=mime argument to the join command.
        msg = mfs("""\
From: anne@example.org
To: test-request@example.com

join digest=no
""")
        self._commandq.enqueue(msg, dict(listname='test@example.com'))
        self._runner.run()
        anne = self._confirm()
        self.assertEqual(anne.address.email, 'anne@example.org')
        self.assertEqual(anne.delivery_mode, DeliveryMode.regular)

    def test_join_with_mime_digests(self):
        # Test the digest=mime argument to the join command.
        msg = mfs("""\
From: anne@example.org
To: test-request@example.com

join digest=mime
""")
        self._commandq.enqueue(msg, dict(listname='test@example.com'))
        self._runner.run()
        anne = self._confirm()
        self.assertEqual(anne.address.email, 'anne@example.org')
        self.assertEqual(anne.delivery_mode, DeliveryMode.mime_digests)

    def test_join_with_plain_digests(self):
        # Test the digest=mime argument to the join command.
        msg = mfs("""\
From: anne@example.org
To: test-request@example.com

join digest=plain
""")
        self._commandq.enqueue(msg, dict(listname='test@example.com'))
        self._runner.run()
        anne = self._confirm()
        self.assertEqual(anne.address.email, 'anne@example.org')
        self.assertEqual(anne.delivery_mode, DeliveryMode.plaintext_digests)
