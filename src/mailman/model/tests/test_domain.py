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

"""Test domains."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.interfaces.domain import (
    DomainCreatedEvent, DomainCreatingEvent, DomainDeletedEvent,
    DomainDeletingEvent, IDomainManager)
from mailman.interfaces.listmanager import IListManager
from mailman.testing.helpers import event_subscribers
from mailman.testing.layers import ConfigLayer



class TestDomainManager(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._events = []

    def _record_event(self, event):
        self._events.append(event)

    def test_create_domain_event(self):
        # Test that creating a domain in the domain manager propagates the
        # expected events.
        with event_subscribers(self._record_event):
            domain = getUtility(IDomainManager).add('example.org')
        self.assertEqual(len(self._events), 2)
        self.assertTrue(isinstance(self._events[0], DomainCreatingEvent))
        self.assertEqual(self._events[0].mail_host, 'example.org')
        self.assertTrue(isinstance(self._events[1], DomainCreatedEvent))
        self.assertEqual(self._events[1].domain, domain)

    def test_delete_domain_event(self):
        # Test that deleting a domain in the domain manager propagates the
        # expected event.
        domain = getUtility(IDomainManager).add('example.org')
        with event_subscribers(self._record_event):
            getUtility(IDomainManager).remove('example.org')
        self.assertEqual(len(self._events), 2)
        self.assertTrue(isinstance(self._events[0], DomainDeletingEvent))
        self.assertEqual(self._events[0].domain, domain)
        self.assertTrue(isinstance(self._events[1], DomainDeletedEvent))
        self.assertEqual(self._events[1].mail_host, 'example.org')



class TestDomainLifecycleEvents(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self._domainmanager = getUtility(IDomainManager)
        self._org = self._domainmanager.add('example.net')
        self._net = self._domainmanager.add('example.org')

    def test_lists_are_deleted_when_domain_is_deleted(self):
        # When a domain is deleted, all the mailing lists in that domain are
        # also deleted.
        create_list('ant@example.net')
        create_list('bee@example.net')
        cat = create_list('cat@example.org')
        dog = create_list('dog@example.org')
        ewe = create_list('ewe@example.com')
        fly = create_list('fly@example.com')
        listmanager = getUtility(IListManager)
        self._domainmanager.remove('example.net')
        self.assertEqual(listmanager.get('ant@example.net'), None)
        self.assertEqual(listmanager.get('bee@example.net'), None)
        self.assertEqual(listmanager.get('cat@example.org'), cat)
        self.assertEqual(listmanager.get('dog@example.org'), dog)
        self.assertEqual(listmanager.get('ewe@example.com'), ewe)
        self.assertEqual(listmanager.get('fly@example.com'), fly)
        self._domainmanager.remove('example.org')
        self.assertEqual(listmanager.get('cat@example.org'), None)
        self.assertEqual(listmanager.get('dog@example.org'), None)
        self.assertEqual(listmanager.get('ewe@example.com'), ewe)
        self.assertEqual(listmanager.get('fly@example.com'), fly)
