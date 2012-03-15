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

"""Test the prototype archiver."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestPrototypeArchiver',
    ]


import os
import shutil
import tempfile
import unittest
import threading

from email import message_from_file
from flufl.lock import Lock

from mailman.app.lifecycle import create_list
from mailman.archiving.prototype import Prototype
from mailman.config import config
from mailman.testing.helpers import LogFileMark
from mailman.testing.helpers import (
    specialized_message_from_string as mfs)
from mailman.testing.layers import ConfigLayer
from mailman.utilities.email import add_message_hash


class TestPrototypeArchiver(unittest.TestCase):
    """Test the prototype archiver."""

    layer = ConfigLayer

    def setUp(self):
        # Create a fake mailing list and message object
        self._msg = mfs("""\
To: test@example.com
From: anne@example.com
Subject: Testing the test list
Message-ID: <ant>
X-Message-ID-Hash: MS6QLWERIJLGCRF44J7USBFDELMNT2BW

Tests are better than no tests
but the water deserves to be swum.
""")
        self._mlist = create_list('test@example.com')
        config.db.commit()
        # Set up a temporary directory for the prototype archiver so that it's
        # easier to clean up.
        self._tempdir = tempfile.mkdtemp()
        config.push('prototype', """
        [paths.testing]
        archive_dir: {0}
        """.format(self._tempdir))
        # Capture the structure of a maildir.
        self._expected_dir_structure = set(
            (os.path.join(config.ARCHIVE_DIR, path) for path in (
                'prototype',
                os.path.join('prototype', self._mlist.fqdn_listname),
                os.path.join('prototype', self._mlist.fqdn_listname, 'cur'),
                os.path.join('prototype', self._mlist.fqdn_listname, 'new'),
                os.path.join('prototype', self._mlist.fqdn_listname, 'tmp'),
                )))
        self._expected_dir_structure.add(config.ARCHIVE_DIR)

    def tearDown(self):
        shutil.rmtree(self._tempdir)
        config.pop('prototype')

    def _find(self, path):
        all_filenames = set()
        for dirpath, dirnames, filenames in os.walk(path):
            if not isinstance(dirpath, unicode):
                dirpath = unicode(dirpath)
            all_filenames.add(dirpath)
            for filename in filenames:
                new_filename = filename
                if not isinstance(filename, unicode):
                    new_filename = unicode(filename)
                all_filenames.add(os.path.join(dirpath, new_filename))
        return all_filenames

    def test_archive_maildir_created(self):
        # Archiving a message to the prototype archiver should create the
        # expected directory structure.
        Prototype.archive_message(self._mlist, self._msg)
        all_filenames = self._find(config.ARCHIVE_DIR)
        # Check that the directory structure has been created and we have one
        # more file (the archived message) than expected directories.
        archived_messages = all_filenames - self._expected_dir_structure
        self.assertEqual(len(archived_messages), 1)
        self.assertTrue(
            archived_messages.pop().startswith(
                os.path.join(config.ARCHIVE_DIR, 'prototype',
                             self._mlist.fqdn_listname, 'new')))

    def test_archive_maildir_existence_does_not_raise(self):
        # Archiving a second message does not cause an EEXIST to be raised
        # when a second message is archived.
        new_dir = None
        Prototype.archive_message(self._mlist, self._msg)
        for directory in ('cur', 'new', 'tmp'):
            path = os.path.join(config.ARCHIVE_DIR, 'prototype',
                                self._mlist.fqdn_listname, directory)
            if directory == 'new':
                new_dir = path
            self.assertTrue(os.path.isdir(path))
        # There should be one message in the 'new' directory.
        self.assertEqual(len(os.listdir(new_dir)), 1)
        # Archive a second message.  If an exception occurs, let it fail the
        # test.  Afterward, two messages should be in the 'new' directory.
        del self._msg['message-id']
        del self._msg['x-message-id-hash']
        self._msg['Message-ID'] = '<bee>'
        add_message_hash(self._msg)
        Prototype.archive_message(self._mlist, self._msg)
        self.assertEqual(len(os.listdir(new_dir)), 2)

    def test_archive_lock_used(self):
        # Test that locking the maildir when adding works as a failure here
        # could mean we lose mail.
        lock_file = os.path.join(
            config.LOCK_DIR, '{0}-maildir.lock'.format(
                self._mlist.fqdn_listname))
        with Lock(lock_file):
            # Acquire the archiver lock, then make sure the archiver logs the
            # fact that it could not acquire the lock.
            archive_thread = threading.Thread(
                target=Prototype.archive_message,
                args=(self._mlist, self._msg))
            mark = LogFileMark('mailman.error')
            archive_thread.run()
            # Test that the archiver output the correct error.
            line = mark.readline()
            # XXX 2012-03-15 BAW: we really should remove timestamp prefixes
            # from the loggers when under test.
            self.assertTrue(line.endswith(
                'Unable to acquire prototype archiver lock for {0}, '
                'discarding: {1}\n'.format(
                    self._mlist.fqdn_listname,
                    self._msg.get('message-id'))))
        # Check that the message didn't get archived.
        created_files = self._find(config.ARCHIVE_DIR)
        self.assertEqual(self._expected_dir_structure, created_files)

    def test_prototype_archiver_good_path(self):
        # Verify the good path; the message gets archived.
        Prototype.archive_message(self._mlist, self._msg)
        new_path = os.path.join(
            config.ARCHIVE_DIR, 'prototype', self._mlist.fqdn_listname, 'new')
        archived_messages = list(os.listdir(new_path))
        self.assertEqual(len(archived_messages), 1)
        # Check that the email has been added.
        with open(os.path.join(new_path, archived_messages[0])) as fp:
            archived_message = message_from_file(fp)
        self.assertEqual(self._msg.as_string(), archived_message.as_string())
