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

"""Test the retry runner."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.runners.retry import RetryRunner
from mailman.testing.helpers import (
    get_queue_messages,
    make_testable_runner,
    specialized_message_from_string as message_from_string)
from mailman.testing.layers import ConfigLayer



class TestRetryRunner(unittest.TestCase):
    """Test the retry runner."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        self._retryq = config.switchboards['retry']
        self._outq = config.switchboards['out']
        self._runner = make_testable_runner(RetryRunner, 'retry')
        self._msg = message_from_string("""\
From: anne@example.com
To: test@example.com
Message-Id: <first>

""")
        self._msgdata = dict(listname='test@example.com')

    def test_message_put_in_outgoing_queue(self):
        self._retryq.enqueue(self._msg, self._msgdata)
        self._runner.run()
        self.assertEqual(len(get_queue_messages('out')), 1)
