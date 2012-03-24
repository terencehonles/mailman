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

"""Test the archive runner."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestArchiveRunner',
    ]


import os
import unittest

from email import message_from_file
from zope.interface import implements

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.archiver import IArchiver
from mailman.runners.archive import ArchiveRunner
from mailman.testing.helpers import (
    make_testable_runner,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer



class DummyArchiver:
    implements(IArchiver)
    name = 'dummy'

    @staticmethod
    def list_url(mlist):
        return 'http://archive.example.com/'

    @staticmethod
    def permalink(mlist, msg):
        filename = msg['x-message-id-hash']
        return 'http://archive.example.com/' + filename
    
    @staticmethod
    def archive_message(mlist, msg):
        filename = msg['x-message-id-hash']
        path = os.path.join(config.MESSAGES_DIR, filename)
        with open(path, 'w') as fp:
            print(msg.as_string(), file=fp)
        # Not technically allowed by the API, but good enough for the test.
        return path



class TestArchiveRunner(unittest.TestCase):
    """Test the archive runner."""

    layer = ConfigLayer

    def setUp(self):
        self._mlist = create_list('test@example.com')
        # Enable just the dummy archiver.
        config.push('dummy', """
        [archiver.dummy]
        class: mailman.runners.tests.test_archiver.DummyArchiver
        enable: yes
        [archiver.prototype]
        enable: no
        [archiver.mhonarc]
        enable: no
        [archiver.mail_archive]
        enable: no
        """)
        self._archiveq = config.switchboards['archive']
        self._msg = mfs("""\
From: aperson@example.com
To: test@example.com
Subject: My first post
Message-ID: <first>
X-Message-ID-Hash: 4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB

First post!
""")
        self._runner = make_testable_runner(ArchiveRunner)

    def tearDown(self):
        config.pop('dummy')

    def test_archive_runner(self):
        # Ensure that the archive runner ends up archiving the message.
        self._archiveq.enqueue(
            self._msg, {}, listname=self._mlist.fqdn_listname)
        self._runner.run()
        # There should now be a copy of the message in the file system.
        filename = os.path.join(
            config.MESSAGES_DIR, '4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB')
        with open(filename) as fp:
            archived = message_from_file(fp)
        self.assertEqual(archived['message-id'], '<first>')

    def test_archive_runner_with_dated_message(self):
        # LP: #963612 FIXME
        self._msg['Date'] = 'Sat, 11 Mar 2011 03:19:38 -0500'
        self._archiveq.enqueue(
            self._msg, {}, listname=self._mlist.fqdn_listname)
        self._runner.run()
        # There should now be a copy of the message in the file system.
        filename = os.path.join(
            config.MESSAGES_DIR, '4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB')
        with open(filename) as fp:
            archived = message_from_file(fp)
        self.assertEqual(archived['message-id'], '<first>')
