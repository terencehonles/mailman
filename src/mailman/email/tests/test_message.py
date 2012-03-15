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

"""Test the message API."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestMessage',
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.email.message import UserNotification
from mailman.testing.helpers import get_queue_messages
from mailman.testing.layers import ConfigLayer



class TestMessage(unittest.TestCase):
    """Test the message API."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._msg = UserNotification(
            'aperson@example.com',
            'test@example.com',
            'Something you need to know',
            'I needed to tell you this.')

    def test_one_precedence_header(self):
        # Ensure that when the original message already has a Precedence:
        # header, UserNotification.send(..., add_precedence=True, ...) does
        # not add a second header.
        self.assertEqual(self._msg['precedence'], None)
        self._msg['Precedence'] = 'omg wtf bbq'
        self._msg.send(self._mlist)
        messages = get_queue_messages('virgin')
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].msg.get_all('precedence'), 
                         ['omg wtf bbq'])
