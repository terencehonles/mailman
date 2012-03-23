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

"""Test posting to a mailing list's -owner address."""

# XXX 2012-03-23 BAW: This is not necessarily the best place for this test.
# We really need a better place to collect these sort of end-to-end posting
# tests.  They're not exactly integration tests, but they do touch lots of
# parts of the system.

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestEmailToOwner',
    ]


import unittest

from operator import itemgetter
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.member import MemberRole
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import (
    TestableMaster,
    get_lmtp_client,
    make_testable_runner)
from mailman.runners.incoming import IncomingRunner
from mailman.runners.outgoing import OutgoingRunner
from mailman.runners.pipeline import PipelineRunner
from mailman.testing.layers import SMTPLayer



class TestEmailToOwner(unittest.TestCase):
    """Test emailing a mailing list's -owner address."""

    layer = SMTPLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        # Add some owners, moderators, and members
        manager = getUtility(IUserManager)
        anne = manager.create_address('anne@example.com')
        bart = manager.create_address('bart@example.com')
        cris = manager.create_address('cris@example.com')
        dave = manager.create_address('dave@example.com')
        self._mlist.subscribe(anne, MemberRole.member)
        self._mlist.subscribe(anne, MemberRole.owner)
        self._mlist.subscribe(bart, MemberRole.moderator)
        self._mlist.subscribe(bart, MemberRole.owner)
        self._mlist.subscribe(cris, MemberRole.moderator)
        self._mlist.subscribe(dave, MemberRole.member)
        config.db.commit()
        self._inq = make_testable_runner(IncomingRunner, 'in')
        self._pipelineq = make_testable_runner(PipelineRunner, 'pipeline')
        self._outq = make_testable_runner(OutgoingRunner, 'out')
        # Python 2.7 has assertMultiLineEqual.  Let this work without bounds.
        self.maxDiff = None
        self.eq = getattr(self, 'assertMultiLineEqual', self.assertEqual)

    def test_owners_get_email(self):
        # XXX 2012-03-23 BAW: We can't use a layer here because we need both
        # the SMTPLayer and LMTPLayer and these are incompatible.  There's no
        # way to make zope.test* happy without causing errors or worse.  Live
        # with this hack until we can rip all that layer crap out and use
        # something like testresources.
        def wait():
            get_lmtp_client(quiet=True)
        lmtpd = TestableMaster(wait)
        lmtpd.start('lmtp')
        # Post a message to the list's -owner address, and all the owners will
        # get a copy of the message.
        lmtp = get_lmtp_client(quiet=True)
        lmtp.lhlo('remote.example.org')
        lmtp.sendmail('zuzu@example.org', ['test-owner@example.com'], """\
From: Zuzu Person <zuzu@example.org>
To: test-owner@example.com
Message-ID: <ant>

Can you help me?
""")
        lmtpd.stop()
        # There should now be one message sitting in the incoming queue.
        # Check that, then process it.  Don't use get_queue_messages() since
        # that will empty the queue.
        self.assertEqual(len(config.switchboards['in'].files), 1)
        self._inq.run()
        # There should now be one message sitting in the pipeline queue.
        # Process that one too.
        self.assertEqual(len(config.switchboards['pipeline'].files), 1)
        self._pipelineq.run()
        # The message has made its way to the outgoing queue.  Again, check
        # and process that one.
        self.assertEqual(len(config.switchboards['out'].files), 1)
        self._outq.run()
        # The SMTP server has now received three messages, one for each of the
        # owners and moderators.  Of course, Bart is both an owner and a
        # moderator, so he'll get only one copy of the message.  Dave does not
        # get a copy of the message.
        messages = sorted(SMTPLayer.smtpd.messages, key=itemgetter('x-rcptto'))
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[0]['x-rcptto'], 'anne@example.com')
        self.assertEqual(messages[1]['x-rcptto'], 'bart@example.com')
        self.assertEqual(messages[2]['x-rcptto'], 'cris@example.com')
        # And yet, all three messages are addressed to the -owner address.
        for message in messages:
            self.assertEqual(message['to'], 'test-owner@example.com')
        # All three messages will have two X-MailFrom headers.  One is added
        # by the LMTP server accepting Zuzu's original message, and will
        # contain her posting address, i.e. zuzu@example.com.  The second one
        # is added by the lazr.smtptest server that accepts Mailman's VERP'd
        # message to the individual recipient.  By verifying both, we prove
        # that Zuzu sent the original message, and that Mailman is VERP'ing
        # the copy to all the owners.
        self.assertEqual(
            messages[0].get_all('x-mailfrom'),
            ['zuzu@example.org', 'test-bounces+anne=example.com@example.com'])
        self.assertEqual(
            messages[1].get_all('x-mailfrom'),
            ['zuzu@example.org', 'test-bounces+bart=example.com@example.com'])
        self.assertEqual(
            messages[2].get_all('x-mailfrom'),
            ['zuzu@example.org', 'test-bounces+cris=example.com@example.com'])
