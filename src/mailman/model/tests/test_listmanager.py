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

"""Test the ListManager."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.interfaces.listmanager import (
    IListManager, ListCreatedEvent, ListDeletedEvent)
from mailman.testing.helpers import event_subscribers
from mailman.testing.layers import ConfigLayer



class TestListManager(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._event = None

    def _record_event(self, event):
        self._event = event

    def test_create_list_event(self):
        # Test that creating a list in the list manager propagates the
        # expected event.
        with event_subscribers(self._record_event):
            mlist = getUtility(IListManager).create('test@example.com')
        self.assertTrue(isinstance(self._event, ListCreatedEvent))
        self.assertEqual(self._event.mailing_list, mlist)

    def test_delete_list_event(self):
        # Test that deleting a list in the list manager propagates the
        # expected event.
        mlist = create_list('another@example.com')
        with event_subscribers(self._record_event):
            getUtility(IListManager).delete(mlist)
        self.assertTrue(isinstance(self._event, ListDeletedEvent))
        self.assertEqual(self._event.fqdn_listname, 'another@example.com')



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestListManager))
    return suite
