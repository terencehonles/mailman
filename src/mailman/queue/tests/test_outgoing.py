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

"""Test the outgoing queue runner."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import datetime
import unittest

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.queue.outgoing import OutgoingRunner
from mailman.testing.helpers import (
    get_queue_messages,
    make_testable_runner,
    specialized_message_from_string as message_from_string)
from mailman.testing.layers import SMTPLayer
from mailman.utilities.datetime import now



def run_once(qrunner):
    """Predicate for make_testable_runner().

    Ensures that the queue runner only runs once.
    """
    return True



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
        # When the metadata has a deliver_after key in the future, the queue
        # runner will re-enqueue the message rather than delivering it.
        deliver_after = now() + datetime.timedelta(days=10)
        self._msgdata['deliver_after'] = deliver_after
        self._outq.enqueue(self._msg, self._msgdata, tolist=True,
                           listname='test@example.com')
        self._runner.run()
        items = get_queue_messages('out')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].msgdata['deliver_after'], deliver_after)
        self.assertEqual(items[0].msg['message-id'], '<first>')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestOnce))
    return suite
