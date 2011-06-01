# Copyright (C) 2011 by the Free Software Foundation, Inc.
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

"""Test the bounce runner."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from zope.component import getUtility

from mailman.app.bounces import send_probe
from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.bounce import (
    BounceContext, IBounceProcessor, UnrecognizedBounceDisposition)
from mailman.interfaces.member import MemberRole
from mailman.interfaces.usermanager import IUserManager
from mailman.runners.bounce import BounceRunner
from mailman.testing.helpers import (
    LogFileMark,
    get_queue_messages,
    make_testable_runner,
    specialized_message_from_string as message_from_string)
from mailman.testing.layers import ConfigLayer



class TestBounceRunner(unittest.TestCase):
    """Test the bounce runner."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._bounceq = config.switchboards['bounces']
        self._runner = make_testable_runner(BounceRunner, 'bounces')
        self._anne = getUtility(IUserManager).create_address(
            'anne@example.com')
        self._member = self._mlist.subscribe(self._anne, MemberRole.member)
        self._msg = message_from_string("""\
From: mail-daemon@example.com
To: test-bounces+anne=example.com@example.com
Message-Id: <first>

""")
        self._msgdata = dict(listname='test@example.com')
        self._processor = getUtility(IBounceProcessor)
        config.push('site owner', """
        [mailman]
        site_owner: postmaster@example.com
        """)

    def tearDown(self):
        config.pop('site owner')

    def test_does_no_processing(self):
        # If the mailing list does no bounce processing, the messages are
        # simply discarded.
        self._mlist.bounce_processing = False
        self._bounceq.enqueue(self._msg, self._msgdata)
        self._runner.run()
        self.assertEqual(len(get_queue_messages('bounces')), 0)
        self.assertEqual(len(list(self._processor.events)), 0)

    def test_verp_detection(self):
        # When we get a VERPd bounce, and we're doing processing, a bounce
        # event will be registered.
        self._bounceq.enqueue(self._msg, self._msgdata)
        self._runner.run()
        self.assertEqual(len(get_queue_messages('bounces')), 0)
        events = list(self._processor.events)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].email, 'anne@example.com')
        self.assertEqual(events[0].list_name, 'test@example.com')
        self.assertEqual(events[0].message_id, '<first>')
        self.assertEqual(events[0].context, BounceContext.normal)
        self.assertEqual(events[0].processed, False)

    def test_nonfatal_verp_detection(self):
        # A VERPd bounce was received, but the error was nonfatal.
        nonfatal = message_from_string("""\
From: mail-daemon@example.com
To: test-bounces+anne=example.com@example.com
Message-Id: <first>
Content-Type: multipart/report; report-type=delivery-status; boundary=AAA
MIME-Version: 1.0

--AAA
Content-Type: message/delivery-status

Action: delayed
Original-Recipient: rfc822; somebody@example.com

--AAA--
""")
        self._bounceq.enqueue(nonfatal, self._msgdata)
        self._runner.run()
        self.assertEqual(len(get_queue_messages('bounces')), 0)
        events = list(self._processor.events)
        self.assertEqual(len(events), 0)

    def test_verp_probe_bounce(self):
        # A VERP probe bounced.  The primary difference here is that the
        # registered bounce event will have a different context.  The
        # Message-Id will be different too, because of the way we're
        # simulating the probe bounce.
        #
        # Start be simulating a probe bounce.
        send_probe(self._member, self._msg)
        message = get_queue_messages('virgin')[0].msg
        bounce = message_from_string("""\
To: {0}
From: mail-daemon@example.com
Message-Id: <second>

""".format(message['From']))
        self._bounceq.enqueue(bounce, self._msgdata)
        self._runner.run()
        self.assertEqual(len(get_queue_messages('bounces')), 0)
        events = list(self._processor.events)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].email, 'anne@example.com')
        self.assertEqual(events[0].list_name, 'test@example.com')
        self.assertEqual(events[0].message_id, '<second>')
        self.assertEqual(events[0].context, BounceContext.probe)
        self.assertEqual(events[0].processed, False)

    def test_nonverp_detectable_fatal_bounce(self):
        # Here's a bounce that is not VERPd, but which has a bouncing address
        # that can be parsed from a known bounce format.  DSN is as good as
        # any, but we'll make the parsed address different for the fun of it.
        dsn = message_from_string("""\
From: mail-daemon@example.com
To: test-bounces@example.com
Message-Id: <first>
Content-Type: multipart/report; report-type=delivery-status; boundary=AAA
MIME-Version: 1.0

--AAA
Content-Type: message/delivery-status

Action: fail
Original-Recipient: rfc822; bart@example.com

--AAA--
""")
        self._bounceq.enqueue(dsn, self._msgdata)
        self._runner.run()
        self.assertEqual(len(get_queue_messages('bounces')), 0)
        events = list(self._processor.events)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].email, 'bart@example.com')
        self.assertEqual(events[0].list_name, 'test@example.com')
        self.assertEqual(events[0].message_id, '<first>')
        self.assertEqual(events[0].context, BounceContext.normal)
        self.assertEqual(events[0].processed, False)

    def test_nonverp_detectable_nonfatal_bounce(self):
        # Here's a bounce that is not VERPd, but which has a bouncing address
        # that can be parsed from a known bounce format.  The bounce is
        # non-fatal so no bounce event is registered.
        dsn = message_from_string("""\
From: mail-daemon@example.com
To: test-bounces@example.com
Message-Id: <first>
Content-Type: multipart/report; report-type=delivery-status; boundary=AAA
MIME-Version: 1.0

--AAA
Content-Type: message/delivery-status

Action: delayed
Original-Recipient: rfc822; bart@example.com

--AAA--
""")
        self._bounceq.enqueue(dsn, self._msgdata)
        self._runner.run()
        self.assertEqual(len(get_queue_messages('bounces')), 0)
        events = list(self._processor.events)
        self.assertEqual(len(events), 0)

    def test_no_detectable_bounce_addresses(self):
        # A bounce message was received, but no addresses could be detected.
        # A message will be logged in the bounce log though, and the message
        # can be forwarded to someone who can do something about it.
        self._mlist.forward_unrecognized_bounces_to = (
            UnrecognizedBounceDisposition.site_owner)
        bogus = message_from_string("""\
From: mail-daemon@example.com
To: test-bounces@example.com
Message-Id: <third>

""")
        self._bounceq.enqueue(bogus, self._msgdata)
        mark = LogFileMark('mailman.bounce')
        self._runner.run()
        self.assertEqual(len(get_queue_messages('bounces')), 0)
        events = list(self._processor.events)
        self.assertEqual(len(events), 0)
        line = mark.readline()
        self.assertEqual(
            line[-51:-1],
            'Bounce message w/no discernable addresses: <third>')
        # Here's the forwarded message to the site owners.
        forwards = get_queue_messages('virgin')
        self.assertEqual(len(forwards), 1)
        self.assertEqual(forwards[0].msg['to'], 'postmaster@example.com')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBounceRunner))
    return suite
