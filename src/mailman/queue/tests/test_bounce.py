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

"""Test the bounce queue runner."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.member import MemberRole
from mailman.interfaces.usermanager import IUserManager
from mailman.queue.bounce import BounceRunner
from mailman.testing.helpers import (
    get_queue_messages,
    make_testable_runner,
    specialized_message_from_string as message_from_string)
from mailman.testing.layers import ConfigLayer



class TestBounceQueue(unittest.TestCase):
    """Test the bounce queue runner."""

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
To: test-bounce+anne=example.com@example.com
Message-Id: <first>

""")
        self._msgdata = dict(listname='test@example.com')

    def test_does_no_processing(self):
        # If the mailing list does no bounce processing, the messages are
        # simply discarded.
        self._mlist.bounce_processing = False
        self._bounceq.enqueue(self._msg, self._msgdata)
        self._runner.run()
        self.assertEqual(len(get_queue_messages('bounces')), 0)



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBounceQueue))
    return suite
