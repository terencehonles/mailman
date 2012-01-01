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

"""Test bounce model objects."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from datetime import datetime
from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.bounce import BounceContext, IBounceProcessor
from mailman.testing.helpers import (
    specialized_message_from_string as message_from_string)
from mailman.testing.layers import ConfigLayer



class TestBounceEvents(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._processor = getUtility(IBounceProcessor)
        self._mlist = create_list('test@example.com')
        self._msg = message_from_string("""\
From: mail-daemon@example.com
To: test-bounces@example.com
Message-Id: <first>

""")

    def test_events_iterator(self):
        self._processor.register(self._mlist, 'anne@example.com', self._msg)
        config.db.commit()
        events = list(self._processor.events)
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.list_name, 'test@example.com')
        self.assertEqual(event.email, 'anne@example.com')
        self.assertEqual(event.timestamp, datetime(2005, 8, 1, 7, 49, 23))
        self.assertEqual(event.message_id, '<first>')
        self.assertEqual(event.context, BounceContext.normal)
        self.assertEqual(event.processed, False)
        # The unprocessed list will be exactly the same right now.
        unprocessed = list(self._processor.unprocessed)
        self.assertEqual(len(unprocessed), 1)
        event = unprocessed[0]
        self.assertEqual(event.list_name, 'test@example.com')
        self.assertEqual(event.email, 'anne@example.com')
        self.assertEqual(event.timestamp, datetime(2005, 8, 1, 7, 49, 23))
        self.assertEqual(event.message_id, '<first>')
        self.assertEqual(event.context, BounceContext.normal)
        self.assertEqual(event.processed, False)

    def test_unprocessed_events_iterator(self):
        self._processor.register(self._mlist, 'anne@example.com', self._msg)
        self._processor.register(self._mlist, 'bart@example.com', self._msg)
        config.db.commit()
        events = list(self._processor.events)
        self.assertEqual(len(events), 2)
        unprocessed = list(self._processor.unprocessed)
        # The unprocessed list will be exactly the same right now.
        self.assertEqual(len(unprocessed), 2)
        # Process one of the events.
        events[0].processed = True
        config.db.commit()
        # Now there will be only one unprocessed event.
        unprocessed = list(self._processor.unprocessed)
        self.assertEqual(len(unprocessed), 1)
        # Process the other event.
        events[1].processed = True
        config.db.commit()
        # Now there will be no unprocessed events.
        unprocessed = list(self._processor.unprocessed)
        self.assertEqual(len(unprocessed), 0)
