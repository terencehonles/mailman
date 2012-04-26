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
from zope.interface import implementer

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.archiver import IArchiver
from mailman.runners.archive import ArchiveRunner
from mailman.testing.helpers import (
    configuration,
    make_testable_runner,
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer
from mailman.utilities.datetime import RFC822_DATE_FMT, factory, now



@implementer(IArchiver)
class DummyArchiver:
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
        self._now = now()
        # Enable just the dummy archiver.
        config.push('dummy', """
        [archiver.dummy]
        class: mailman.runners.tests.test_archiver.DummyArchiver
        enable: no
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

    @configuration('archiver.dummy', enable='yes')
    def test_archive_runner(self):
        # Ensure that the archive runner ends up archiving the message.
        self._archiveq.enqueue(
            self._msg, {},
            listname=self._mlist.fqdn_listname,
            received_time=now())
        self._runner.run()
        # There should now be a copy of the message in the file system.
        filename = os.path.join(
            config.MESSAGES_DIR, '4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB')
        with open(filename) as fp:
            archived = message_from_file(fp)
        self.assertEqual(archived['message-id'], '<first>')

    @configuration('archiver.dummy', enable='yes')
    def test_archive_runner_with_dated_message(self):
        # Date headers don't throw off the archiver runner.
        self._msg['Date'] = now(strip_tzinfo=False).strftime(RFC822_DATE_FMT)
        self._archiveq.enqueue(
            self._msg, {},
            listname=self._mlist.fqdn_listname,
            received_time=now())
        self._runner.run()
        # There should now be a copy of the message in the file system.
        filename = os.path.join(
            config.MESSAGES_DIR, '4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB')
        with open(filename) as fp:
            archived = message_from_file(fp)
        self.assertEqual(archived['message-id'], '<first>')
        self.assertEqual(archived['date'], 'Mon, 01 Aug 2005 07:49:23 +0000')

    @configuration('archiver.dummy', enable='yes', clobber_date='never')
    def test_clobber_date_never(self):
        # Even if the Date header is insanely off from the received time of
        # the message, if clobber_date is 'never', the header is not clobbered.
        self._msg['Date'] = now(strip_tzinfo=False).strftime(RFC822_DATE_FMT)
        self._archiveq.enqueue(
            self._msg, {},
            listname=self._mlist.fqdn_listname,
            received_time=now())
        self._runner.run()
        # There should now be a copy of the message in the file system.
        filename = os.path.join(
            config.MESSAGES_DIR, '4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB')
        with open(filename) as fp:
            archived = message_from_file(fp)
        self.assertEqual(archived['message-id'], '<first>')
        self.assertEqual(archived['date'], 'Mon, 01 Aug 2005 07:49:23 +0000')

    @configuration('archiver.dummy', enable='yes')
    def test_clobber_dateless(self):
        # A message with no Date header will always get clobbered.
        self.assertEqual(self._msg['date'], None)
        # Now, before enqueuing the message (well, really, calling 'now()'
        # again), fast forward a few days.
        self._archiveq.enqueue(
            self._msg, {},
            listname=self._mlist.fqdn_listname,
            received_time=now(strip_tzinfo=False))
        self._runner.run()
        # There should now be a copy of the message in the file system.
        filename = os.path.join(
            config.MESSAGES_DIR, '4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB')
        with open(filename) as fp:
            archived = message_from_file(fp)
        self.assertEqual(archived['message-id'], '<first>')
        self.assertEqual(archived['date'], 'Mon, 01 Aug 2005 07:49:23 +0000')

    @configuration('archiver.dummy', enable='yes', clobber_date='always')
    def test_clobber_date_always(self):
        # The date always gets clobbered with the current received time.
        self._msg['Date'] = now(strip_tzinfo=False).strftime(RFC822_DATE_FMT)
        # Now, before enqueuing the message (well, really, calling 'now()'
        # again as will happen in the runner), fast forward a few days.
        self._archiveq.enqueue(
            self._msg, {},
            listname=self._mlist.fqdn_listname)
        factory.fast_forward(days=4)
        self._runner.run()
        # There should now be a copy of the message in the file system.
        filename = os.path.join(
            config.MESSAGES_DIR, '4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB')
        with open(filename) as fp:
            archived = message_from_file(fp)
        self.assertEqual(archived['message-id'], '<first>')
        self.assertEqual(archived['date'], 'Fri, 05 Aug 2005 07:49:23 +0000')
        self.assertEqual(archived['x-original-date'],
                         'Mon, 01 Aug 2005 07:49:23 +0000')

    @configuration('archiver.dummy',
                   enable='yes', clobber_date='maybe', clobber_skew='1d')
    def test_clobber_date_maybe_when_insane(self):
        # The date is clobbered if it's farther off from now than its skew
        # period.
        self._msg['Date'] = now(strip_tzinfo=False).strftime(RFC822_DATE_FMT)
        # Now, before enqueuing the message (well, really, calling 'now()'
        # again as will happen in the runner), fast forward a few days.
        self._archiveq.enqueue(
            self._msg, {},
            listname=self._mlist.fqdn_listname)
        factory.fast_forward(days=4)
        self._runner.run()
        # There should now be a copy of the message in the file system.
        filename = os.path.join(
            config.MESSAGES_DIR, '4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB')
        with open(filename) as fp:
            archived = message_from_file(fp)
        self.assertEqual(archived['message-id'], '<first>')
        self.assertEqual(archived['date'], 'Fri, 05 Aug 2005 07:49:23 +0000')
        self.assertEqual(archived['x-original-date'],
                         'Mon, 01 Aug 2005 07:49:23 +0000')

    @configuration('archiver.dummy',
                   enable='yes', clobber_date='maybe', clobber_skew='10d')
    def test_clobber_date_maybe_when_sane(self):
        # The date is not clobbered if it's nearer to now than its skew
        # period.
        self._msg['Date'] = now(strip_tzinfo=False).strftime(RFC822_DATE_FMT)
        # Now, before enqueuing the message (well, really, calling 'now()'
        # again as will happen in the runner), fast forward a few days.
        self._archiveq.enqueue(
            self._msg, {},
            listname=self._mlist.fqdn_listname)
        factory.fast_forward(days=4)
        self._runner.run()
        # There should now be a copy of the message in the file system.
        filename = os.path.join(
            config.MESSAGES_DIR, '4CMWUN6BHVCMHMDAOSJZ2Q72G5M32MWB')
        with open(filename) as fp:
            archived = message_from_file(fp)
        self.assertEqual(archived['message-id'], '<first>')
        self.assertEqual(archived['date'], 'Mon, 01 Aug 2005 07:49:23 +0000')
        self.assertEqual(archived['x-original-date'], None)
