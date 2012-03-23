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

"""Test the owner chain."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestOwnerChain',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.chains.owner import BuiltInOwnerChain, OwnerNotification
from mailman.core.chains import process
from mailman.testing.helpers import (
    event_subscribers,
    get_queue_messages,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class TestOwnerChain(unittest.TestCase):
    """Test the owner chain."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._msg = mfs("""\
From: anne@example.com
To: test@example.com
Message-ID: <ant>

""")

    def test_owner_pipeline(self):
        # Messages processed through the default owners chain end up in the
        # pipeline queue, and an event gets sent.
        #
        # This event subscriber records the event that occurs when the message
        # is processed by the owner chain.
        events = []
        def catch_event(event):
            events.append(event)
        with event_subscribers(catch_event):
            process(self._mlist, self._msg, {}, 'default-owner-chain')
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertTrue(isinstance(event, OwnerNotification))
        self.assertEqual(event.mlist, self._mlist)
        self.assertEqual(event.msg['message-id'], '<ant>')
        self.assertTrue(isinstance(event.chain, BuiltInOwnerChain))
        messages = get_queue_messages('pipeline')
        self.assertEqual(len(messages), 1)
        message = messages[0].msg
        self.assertEqual(message['message-id'], '<ant>')
