# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""Test the outgoing runner."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import os
import socket
import logging
import unittest

from contextlib import contextmanager
from datetime import datetime, timedelta
from lazr.config import as_timedelta
from zope.component import getUtility

from mailman.app.bounces import send_probe
from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.bounce import BounceContext, IBounceProcessor
from mailman.interfaces.mailinglist import Personalization
from mailman.interfaces.member import MemberRole
from mailman.interfaces.mta import SomeRecipientsFailed
from mailman.interfaces.pending import IPendings
from mailman.interfaces.usermanager import IUserManager
from mailman.runners.outgoing import OutgoingRunner
from mailman.testing.helpers import (
    LogFileMark,
    get_queue_messages,
    make_testable_runner,
    specialized_message_from_string as message_from_string)
from mailman.testing.layers import ConfigLayer, SMTPLayer
from mailman.utilities.datetime import factory, now



def run_once(runner):
    """Predicate for make_testable_runner().

    Ensures that the runner only runs once.
    """
    return True


@contextmanager
def temporary_config(name, settings):
    """Temporarily set a configuration (use in a with-statement)."""
    config.push(name, settings)
    try:
        yield
    finally:
        config.pop(name)



class TestOnce(unittest.TestCase):
    """Test outgoing runner message disposition."""

    layer = SMTPLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._outq = config.switchboards['out']
        self._runner = make_testable_runner(OutgoingRunner, 'out', run_once)
        self._msg = message_from_string("""\
From: anne@example.com
To: test@example.com
Message-Id: <first>

""")
        self._msgdata = {}

    def test_deliver_after(self):
        # When the metadata has a deliver_after key in the future, the runner
        # will re-enqueue the message rather than delivering it.
        deliver_after = now() + timedelta(days=10)
        self._msgdata['deliver_after'] = deliver_after
        self._outq.enqueue(self._msg, self._msgdata,
                           tolist=True, listname='test@example.com')
        self._runner.run()
        items = get_queue_messages('out')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].msgdata['deliver_after'], deliver_after)
        self.assertEqual(items[0].msg['message-id'], '<first>')



captured_mlist = None
captured_msg = None
captured_msgdata = None

def capture(mlist, msg, msgdata):
    global captured_mlist, captured_msg, captured_msgdata
    captured_mlist = mlist
    captured_msg = msg
    captured_msgdata = msgdata


class TestVERPSettings(unittest.TestCase):
    """Test the selection of VERP based on various criteria."""

    layer = ConfigLayer

    def setUp(self):
        global captured_mlist, captured_msg, captured_msgdata
        # Push a config where actual delivery is handled by a dummy function.
        # We generally don't care what this does, since we're just testing the
        # setting of the 'verp' key in the metadata.
        config.push('fake outgoing', """
        [mta]
        outgoing: mailman.runners.tests.test_outgoing.capture
        """)
        # Reset the captured data.
        captured_mlist = None
        captured_msg = None
        captured_msgdata = None
        self._mlist = create_list('test@example.com')
        self._outq = config.switchboards['out']
        self._runner = make_testable_runner(OutgoingRunner, 'out')
        self._msg = message_from_string("""\
From: anne@example.com
To: test@example.com
Message-Id: <first>

""")

    def tearDown(self):
        config.pop('fake outgoing')

    def test_delivery_callback(self):
        # Test that the configuration variable calls the appropriate callback.
        self._outq.enqueue(self._msg, {}, listname='test@example.com')
        self._runner.run()
        self.assertEqual(captured_mlist, self._mlist)
        self.assertEqual(captured_msg.as_string(), self._msg.as_string())
        # Of course, the message metadata will contain a bunch of keys added
        # by the processing.  We don't really care about the details, so this
        # test is a good enough stand-in.
        self.assertEqual(captured_msgdata['listname'], 'test@example.com')

    def test_verp_in_metadata(self):
        # Test that if the metadata has a 'verp' key, it is unchanged.
        marker = 'yepper'
        msgdata = dict(verp=marker)
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        self._runner.run()
        self.assertEqual(captured_msgdata['verp'], marker)

    def test_personalized_individual_deliveries_verp(self):
        # When deliveries are personalized, and the configuration setting
        # indicates, messages will be VERP'd.
        msgdata = {}
        self._mlist.personalize = Personalization.individual
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        with temporary_config('personalize', """
        [mta]
        verp_personalized_deliveries: yes
        """):
            self._runner.run()
        self.assertTrue(captured_msgdata['verp'])

    def test_personalized_full_deliveries_verp(self):
        # When deliveries are personalized, and the configuration setting
        # indicates, messages will be VERP'd.
        msgdata = {}
        self._mlist.personalize = Personalization.full
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        with temporary_config('personalize', """
        [mta]
        verp_personalized_deliveries: yes
        """):
            self._runner.run()
        self.assertTrue(captured_msgdata['verp'])

    def test_personalized_deliveries_no_verp(self):
        # When deliveries are personalized, but the configuration setting
        # does not indicate, messages will not be VERP'd.
        msgdata = {}
        self._mlist.personalize = Personalization.full
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        self._runner.run()
        self.assertFalse('verp' in captured_msgdata)

    def test_verp_never(self):
        # Never VERP when the interval is zero.
        msgdata = {}
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        with temporary_config('personalize', """
        [mta]
        verp_delivery_interval: 0
        """):
            self._runner.run()
        self.assertEqual(captured_msgdata['verp'], False)

    def test_verp_always(self):
        # Always VERP when the interval is one.
        msgdata = {}
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        with temporary_config('personalize', """
        [mta]
        verp_delivery_interval: 1
        """):
            self._runner.run()
        self.assertEqual(captured_msgdata['verp'], True)

    def test_verp_on_interval_match(self):
        # VERP every so often, when the post_id matches.
        self._mlist.post_id = 5
        msgdata = {}
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        with temporary_config('personalize', """
        [mta]
        verp_delivery_interval: 5
        """):
            self._runner.run()
        self.assertEqual(captured_msgdata['verp'], True)

    def test_no_verp_on_interval_miss(self):
        # VERP every so often, when the post_id matches.
        self._mlist.post_id = 4
        msgdata = {}
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        with temporary_config('personalize', """
            [mta]
            verp_delivery_interval: 5
            """):
            self._runner.run()
        self.assertEqual(captured_msgdata['verp'], False)



def raise_socket_error(mlist, msg, msgdata):
    raise socket.error


class TestSocketError(unittest.TestCase):
    """Test socket.error occurring in the delivery function."""

    layer = ConfigLayer

    def setUp(self):
        # Push a config where actual delivery is handled by a dummy function.
        # We generally don't care what this does, since we're just testing the
        # setting of the 'verp' key in the metadata.
        config.push('fake outgoing', """
        [mta]
        outgoing: mailman.runners.tests.test_outgoing.raise_socket_error
        """)
        self._mlist = create_list('test@example.com')
        self._outq = config.switchboards['out']
        self._runner = make_testable_runner(OutgoingRunner, 'out', run_once)
        self._msg = message_from_string("""\
From: anne@example.com
To: test@example.com
Message-Id: <first>

""")

    def tearDown(self):
        config.pop('fake outgoing')

    def test_error_with_port_0(self):
        # Test the code path where a socket.error is raised in the delivery
        # function, and the MTA port is set to zero.  The only real effect of
        # that is a log message.  Start by opening the error log and reading
        # the current file position.
        error_log = logging.getLogger('mailman.error')
        filename = error_log.handlers[0].filename
        filepos = os.stat(filename).st_size
        self._outq.enqueue(self._msg, {}, listname='test@example.com')
        with temporary_config('port 0', """
            [mta]
            smtp_port: 0
            """):
            self._runner.run()
        with open(filename) as fp:
            fp.seek(filepos)
            line = fp.readline()
        # The log line will contain a variable timestamp, the PID, and a
        # trailing newline.  Ignore these.
        self.assertEqual(
            line[-53:-1],
            'Cannot connect to SMTP server localhost on port smtp')

    def test_error_with_numeric_port(self):
        # Test the code path where a socket.error is raised in the delivery
        # function, and the MTA port is set to zero.  The only real effect of
        # that is a log message.  Start by opening the error log and reading
        # the current file position.
        mark = LogFileMark('mailman.error')
        self._outq.enqueue(self._msg, {}, listname='test@example.com')
        with temporary_config('port 0', """
            [mta]
            smtp_port: 2112
            """):
            self._runner.run()
        line = mark.readline()
        # The log line will contain a variable timestamp, the PID, and a
        # trailing newline.  Ignore these.
        self.assertEqual(
            line[-53:-1],
            'Cannot connect to SMTP server localhost on port 2112')



temporary_failures = []
permanent_failures = []


def raise_SomeRecipientsFailed(mlist, msg, msgdata):
    raise SomeRecipientsFailed(temporary_failures, permanent_failures)


class TestSomeRecipientsFailed(unittest.TestCase):
    """Test socket.error occurring in the delivery function."""

    layer = ConfigLayer

    def setUp(self):
        global temporary_failures, permanent_failures
        del temporary_failures[:]
        del permanent_failures[:]
        self._processor = getUtility(IBounceProcessor)
        # Push a config where actual delivery is handled by a dummy function.
        # We generally don't care what this does, since we're just testing the
        # setting of the 'verp' key in the metadata.
        config.push('fake outgoing', """
       [mta]
       outgoing: mailman.runners.tests.test_outgoing.raise_SomeRecipientsFailed
        """)
        self._mlist = create_list('test@example.com')
        self._outq = config.switchboards['out']
        self._runner = make_testable_runner(OutgoingRunner, 'out', run_once)
        self._msg = message_from_string("""\
From: anne@example.com
To: test@example.com
Message-Id: <first>

""")

    def tearDown(self):
        config.pop('fake outgoing')

    def test_probe_failure(self):
        # When a probe message fails during SMTP, a bounce event is recorded
        # with the proper bounce context.
        anne = getUtility(IUserManager).create_address('anne@example.com')
        member = self._mlist.subscribe(anne, MemberRole.member)
        token = send_probe(member, self._msg)
        msgdata = dict(probe_token=token)
        permanent_failures.append('anne@example.com')
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        self._runner.run()
        events = list(self._processor.unprocessed)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.list_name, 'test@example.com')
        self.assertEqual(event.email, 'anne@example.com')
        self.assertEqual(event.timestamp, datetime(2005, 8, 1, 7, 49, 23))
        self.assertEqual(event.message_id, '<first>')
        self.assertEqual(event.context, BounceContext.probe)
        self.assertEqual(event.processed, False)

    def test_confirmed_probe_failure(self):
        # This time, a probe also fails, but for some reason the probe token
        # has already been confirmed and no longer exists in the database.
        anne = getUtility(IUserManager).create_address('anne@example.com')
        member = self._mlist.subscribe(anne, MemberRole.member)
        token = send_probe(member, self._msg)
        getUtility(IPendings).confirm(token)
        msgdata = dict(probe_token=token)
        permanent_failures.append('anne@example.com')
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        self._runner.run()
        events = list(self._processor.unprocessed)
        self.assertEqual(len(events), 0)

    def test_probe_temporary_failure(self):
        # This time, a probe also fails, but the failures are temporary so
        # they are not registered.
        anne = getUtility(IUserManager).create_address('anne@example.com')
        member = self._mlist.subscribe(anne, MemberRole.member)
        token = send_probe(member, self._msg)
        getUtility(IPendings).confirm(token)
        msgdata = dict(probe_token=token)
        temporary_failures.append('anne@example.com')
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        self._runner.run()
        events = list(self._processor.unprocessed)
        self.assertEqual(len(events), 0)

    def test_one_permanent_failure(self):
        # Normal (i.e. non-probe) permanent failures just get registered.
        permanent_failures.append('anne@example.com')
        self._outq.enqueue(self._msg, {}, listname='test@example.com')
        self._runner.run()
        events = list(self._processor.unprocessed)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].email, 'anne@example.com')
        self.assertEqual(events[0].context, BounceContext.normal)

    def test_two_permanent_failures(self):
        # Two normal (i.e. non-probe) permanent failures just get registered.
        permanent_failures.append('anne@example.com')
        permanent_failures.append('bart@example.com')
        self._outq.enqueue(self._msg, {}, listname='test@example.com')
        self._runner.run()
        events = list(self._processor.unprocessed)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].email, 'anne@example.com')
        self.assertEqual(events[0].context, BounceContext.normal)
        self.assertEqual(events[1].email, 'bart@example.com')
        self.assertEqual(events[1].context, BounceContext.normal)

    def test_one_temporary_failure(self):
        # The first time there are temporary failures, the message just gets
        # put in the retry queue, but with some metadata to prevent infinite
        # retries.
        temporary_failures.append('cris@example.com')
        self._outq.enqueue(self._msg, {}, listname='test@example.com')
        self._runner.run()
        events = list(self._processor.unprocessed)
        self.assertEqual(len(events), 0)
        items = get_queue_messages('retry')
        self.assertEqual(len(items), 1)
        self.assertEqual(self._msg.as_string(), items[0].msg.as_string())
        # The metadata has three keys which are used two decide whether the
        # next temporary failure should be retried.
        self.assertEqual(items[0].msgdata['last_recip_count'], 1)
        deliver_until = (datetime(2005, 8, 1, 7, 49, 23) +
                         as_timedelta(config.mta.delivery_retry_period))
        self.assertEqual(items[0].msgdata['deliver_until'], deliver_until)
        self.assertEqual(items[0].msgdata['recipients'], ['cris@example.com'])

    def test_two_temporary_failures(self):
        # The first time there are temporary failures, the message just gets
        # put in the retry queue, but with some metadata to prevent infinite
        # retries.
        temporary_failures.append('cris@example.com')
        temporary_failures.append('dave@example.com')
        self._outq.enqueue(self._msg, {}, listname='test@example.com')
        self._runner.run()
        events = list(self._processor.unprocessed)
        self.assertEqual(len(events), 0)
        items = get_queue_messages('retry')
        # There's still only one item in the retry queue, but the metadata
        # contains both temporary failures.
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].msgdata['last_recip_count'], 2)
        self.assertEqual(items[0].msgdata['recipients'],
                         ['cris@example.com', 'dave@example.com'])

    def test_mixed_failures(self):
        # Some temporary and some permanent failures.
        permanent_failures.append('elle@example.com')
        permanent_failures.append('fred@example.com')
        temporary_failures.append('gwen@example.com')
        temporary_failures.append('herb@example.com')
        self._outq.enqueue(self._msg, {}, listname='test@example.com')
        self._runner.run()
        # Let's look at the permanent failures.
        events = list(self._processor.unprocessed)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].email, 'elle@example.com')
        self.assertEqual(events[0].context, BounceContext.normal)
        self.assertEqual(events[1].email, 'fred@example.com')
        self.assertEqual(events[1].context, BounceContext.normal)
        # Let's look at the temporary failures.
        items = get_queue_messages('retry')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].msgdata['recipients'],
                         ['gwen@example.com', 'herb@example.com'])

    def test_no_progress_on_retries_within_retry_period(self):
        # Temporary failures cause queuing for a retry later on, unless no
        # progress is being made on the retries and we've tried for the
        # specified delivery retry period.  This test ensures that even if no
        # progress is made, if the retry period hasn't expired, the message
        # will be requeued.
        temporary_failures.append('iona@example.com')
        temporary_failures.append('jeff@example.com')
        deliver_until = (datetime(2005, 8, 1, 7, 49, 23) +
                         as_timedelta(config.mta.delivery_retry_period))
        msgdata = dict(last_recip_count=2,
                       deliver_until=deliver_until)
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        self._runner.run()
        # The retry queue should have our message waiting to be retried.
        items = get_queue_messages('retry')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].msgdata['deliver_until'], deliver_until)
        self.assertEqual(items[0].msgdata['recipients'],
                         ['iona@example.com', 'jeff@example.com'])

    def test_no_progress_on_retries_with_expired_retry_period(self):
        # We've had temporary failures with no progress, and the retry period
        # has expired.  In that case, a log entry is written and message is
        # discarded.  There's nothing more that can be done.
        temporary_failures.append('kira@example.com')
        temporary_failures.append('lonn@example.com')
        retry_period = as_timedelta(config.mta.delivery_retry_period)
        deliver_until = datetime(2005, 8, 1, 7, 49, 23) + retry_period
        msgdata = dict(last_recip_count=2,
                       deliver_until=deliver_until)
        self._outq.enqueue(self._msg, msgdata, listname='test@example.com')
        # Before the runner runs, several days pass.
        factory.fast_forward(retry_period.days + 1)
        mark = LogFileMark('mailman.smtp')
        self._runner.run()
        # There should be no message in the retry or outgoing queues.
        self.assertEqual(len(get_queue_messages('retry')), 0)
        self.assertEqual(len(get_queue_messages('out')), 0)
        # There should be a log message in the smtp log indicating that the
        # message has been discarded.
        line = mark.readline()
        self.assertEqual(
            line[-63:-1],
            'Discarding message with persistent temporary failures: <first>')
