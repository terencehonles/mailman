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

"""Additional tests for the hold chain."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.chains.hold import autorespond_to_sender
from mailman.config import config
from mailman.interfaces.autorespond import IAutoResponseSet, Response
from mailman.interfaces.usermanager import IUserManager
from mailman.testing.helpers import get_queue_messages
from mailman.testing.layers import ConfigLayer



class TestAutorespond(unittest.TestCase):
    """Test autorespond_to_sender()"""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        # Python 2.7 has assertMultiLineEqual.  Let this work without bounds.
        self.maxDiff = None
        self.eq = getattr(self, 'assertMultiLineEqual', self.assertEqual)

    def test_max_autoresponses_per_day(self):
        # The last one we sent was the last one we should send today.  Instead
        # of sending an automatic response, send them the "no more today"
        # message.
        config.push('max-1', """
        [mta]
        max_autoresponses_per_day: 1
        """)
        # Simulate a response having been sent to an address already.
        anne = getUtility(IUserManager).create_address('anne@example.com')
        response_set = IAutoResponseSet(self._mlist)
        response_set.response_sent(anne, Response.hold)
        # Trigger the sending of a "last response for today" using the default
        # language (i.e. the mailing list's preferred language).
        autorespond_to_sender(self._mlist, 'anne@example.com')
        # So first, there should be one more hold response sent to the user.
        self.assertEqual(response_set.todays_count(anne, Response.hold), 2)
        # And the virgin queue should have the message in it.
        messages = get_queue_messages('virgin')
        self.assertEqual(len(messages), 1)
        # Remove the variable headers.
        message = messages[0].msg
        self.assertTrue('message-id' in message)
        del message['message-id']
        self.assertTrue('date' in message)
        del message['date']
        self.eq(messages[0].msg.as_string(), """\
MIME-Version: 1.0
Content-Type: text/plain; charset="us-ascii"
Content-Transfer-Encoding: 7bit
Subject: Last autoresponse notification for today
From: test-owner@example.com
To: anne@example.com
Precedence: bulk

We have received a message from your address <anne@example.com>
requesting an automated response from the test@example.com mailing
list.

The number we have seen today: 1.  In order to avoid problems such as
mail loops between email robots, we will not be sending you any
further responses today.  Please try again tomorrow.

If you believe this message is in error, or if you have any questions,
please contact the list owner at test-owner@example.com.""")
