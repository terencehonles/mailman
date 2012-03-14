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
    ]

import os
import shutil
import tempfile
import unittest
import threading

from flufl.lock import Lock

from mailman.app.lifecycle import create_list
from mailman.archiving import prototype
from mailman.config import config
from mailman.testing.helpers import LogFileMark
from mailman.testing.helpers import specialized_message_from_string as smfs
from mailman.testing.layers import ConfigLayer


class test_PrototypeArchiveMethod(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        # Create a fake mailing list and message object
        self.message = smfs('''\
To: test@example.com
From: admin@example.com
Subject: Testing the test list
Message-ID: <DEADBEEF@example.com>

Tests are better than not tests
but the water deserves to be swum
                ''')

        self.mlist = create_list('test@example.com')
        config.db.commit()

        # Set some config directories where we won't bash real data
        config.ARCHIVE_DIR = '%s%s' % (tempfile.mkdtemp(), os.path.sep)
        config.LOCK_DIR = tempfile.mkdtemp()

        # Structure of a maildir
        self.expected_dir_structure = frozenset(
                (os.path.join(config.ARCHIVE_DIR, f) for f in (
                    '',
                    'prototype',
                    os.path.join('prototype', self.mlist.fqdn_listname),
                    os.path.join('prototype', self.mlist.fqdn_listname, 'cur'),
                    os.path.join('prototype', self.mlist.fqdn_listname, 'new'),
                    os.path.join('prototype', self.mlist.fqdn_listname, 'tmp'),
                    )
                    )
                )

    def tearDown(self):
        shutil.rmtree(config.ARCHIVE_DIR)
        shutil.rmtree(config.LOCK_DIR)

    def _find(self, path):
        all_filenames = set()
        for dirs in os.walk(path):
            directory = dirs[0]
            if not isinstance(directory, unicode):
                directory = unicode(directory)
            all_filenames.add(directory)
            if dirs[2]:
                for filename in dirs[2]:
                    new_filename = os.path.join(dirs[0], filename)
                    if not isinstance(new_filename, unicode):
                        new_filename = unicode(new_filename)
                    all_filenames.add(new_filename)
        return all_filenames

    def test_archive_maildir_created(self):
        prototype.Prototype.archive_message(self.mlist, self.message)
        all_filenames = self._find(config.ARCHIVE_DIR)
        # Check that the directory structure has been created and we have one
        # more file (the archived message) than expected directories
        self.assertTrue(self.expected_dir_structure.issubset(all_filenames))
        self.assertEqual(len(all_filenames), len(self.expected_dir_structure) + 1)

    def test_archive_maildir_existance_does_not_raise(self):
        os.makedirs(os.path.join(config.ARCHIVE_DIR, 'prototype',
            self.mlist.fqdn_listname, 'cur'))
        os.mkdir(os.path.join(config.ARCHIVE_DIR, 'prototype',
            self.mlist.fqdn_listname, 'new'))
        os.mkdir(os.path.join(config.ARCHIVE_DIR, 'prototype',
            self.mlist.fqdn_listname, 'tmp'))

        # Checking that no exception is raised in this circumstance because it
        # will be the common case (adding a new message to an archive whose
        # directories have alreay been created)
        try:
            prototype.Prototype.archive_message(self.mlist, self.message)
        except:
            self.assertTrue(False, 'Exception raised when the archive'
                    ' directory structure already in place')

    def test_archive_lock_used(self):
        # Test that locking the maildir when adding works as a failure here
        # could mean we lose mail
        lock = Lock(os.path.join(config.LOCK_DIR, '%s-maildir.lock'
            % self.mlist.fqdn_listname))
        with lock:
            # Take this lock.  Then make sure the archiver fails while that's
            # working.
            archive_thread = threading.Thread(
                    target=prototype.Prototype.archive_message,
                    args=(self.mlist, self.message))
            mark = LogFileMark('mailman.error')
            archive_thread.run()
            # Test that the archiver output the correct error
            line = mark.readline()
            self.assertTrue(line.endswith('Unable to lock archive for %s,'
                    ' discarded message: %s\n' % (self.mlist.fqdn_listname,
                        self.message.get('message-id'))))

        # Check that the file didn't get created
        created_files = self._find(config.ARCHIVE_DIR)
        self.assertEqual(self.expected_dir_structure, created_files)

    def test_mail_added(self):
        prototype.Prototype.archive_message(self.mlist, self.message)
        for filename in os.listdir(os.path.join(config.ARCHIVE_DIR,
                'prototype', self.mlist.fqdn_listname, 'new')):
            # Check that the email has been added
            email = open(os.path.join(config.ARCHIVE_DIR, 'prototype',
                    self.mlist.fqdn_listname, 'new', filename))
            self.assertTrue((repr(self.message)).endswith(email.read()))
