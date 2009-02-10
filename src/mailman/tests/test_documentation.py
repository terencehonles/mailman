# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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

"""Harness for testing Mailman's documentation.

Note that doctest extraction does not currently work for zip file
distributions.  doctest discovery currently requires file system traversal.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import os
import random
import doctest
import unittest

from email import message_from_string

import mailman

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.email.message import Message
from mailman.testing.layers import SMTPLayer


DOT = '.'
COMMASPACE = ', '



class chdir:
    """A context manager for temporary directory changing."""
    def __init__(self, directory):
        self._curdir = None
        self._directory = directory

    def __enter__(self):
        self._curdir = os.getcwd()
        os.chdir(self._directory)

    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self._curdir)
        # Don't suppress exceptions.
        return False



def specialized_message_from_string(text):
    """Parse text into a message object.

    This is specialized in the sense that an instance of Mailman's own Message
    object is returned, and this message object has an attribute
    `original_size` which is the pre-calculated size in bytes of the message's
    text representation.
    """
    # This mimic what Switchboard.dequeue() does when parsing a message from
    # text into a Message instance.
    original_size = len(text)
    message = message_from_string(text, Message)
    message.original_size = original_size
    return message


def stop():
    """Call into pdb.set_trace()"""
    # Do the import here so that you get the wacky special hacked pdb instead
    # of Python's normal pdb.
    import pdb
    pdb.set_trace()


def dump_msgdata(msgdata, *additional_skips):
    """Dump in a more readable way a message metadata dictionary."""
    skips = set(additional_skips)
    # Some stuff we always want to skip, because their values will always be
    # variable data.
    skips.add('received_time')
    longest = max(len(key) for key in msgdata if key not in skips)
    for key in sorted(msgdata):
        if key in skips:
            continue
        print '{0:{2}}: {1}'.format(key, msgdata[key], longest)



def setup(testobj):
    """Test setup."""
    # In general, I don't like adding convenience functions, since I think
    # doctests should do the imports themselves.  It makes for better
    # documentation that way.  However, a few are really useful, or help to
    # hide some icky test implementation details.
    testobj.globs['commit'] = config.db.commit
    testobj.globs['config'] = config
    testobj.globs['create_list'] = create_list
    testobj.globs['dump_msgdata'] = dump_msgdata
    testobj.globs['message_from_string'] = specialized_message_from_string
    testobj.globs['smtpd'] = SMTPLayer.smtpd
    testobj.globs['stop'] = stop



def test_suite():
    suite = unittest.TestSuite()
    topdir = os.path.dirname(mailman.__file__)
    packages = []
    for dirpath, dirnames, filenames in os.walk(topdir):
        if 'docs' in dirnames:
            docsdir = os.path.join(dirpath, 'docs')[len(topdir)+1:]
            packages.append(docsdir)
    # Under higher verbosity settings, report all doctest errors, not just the
    # first one.
    flags = (doctest.ELLIPSIS |
             doctest.NORMALIZE_WHITESPACE |
             doctest.REPORT_NDIFF)
    # Add all the doctests in all subpackages.
    doctest_files = {}
    with chdir(topdir):
        for docsdir in packages:
            for filename in os.listdir(docsdir):
                if os.path.splitext(filename)[1] == '.txt':
                    doctest_files[filename] = os.path.join(docsdir, filename)
    files = sorted(doctest_files)
    for filename in files:
        path = doctest_files[filename]
        test = doctest.DocFileSuite(
            path,
            package='mailman',
            optionflags=flags,
            setUp=setup)
        test.layer = SMTPLayer
        suite.addTest(test)
    return suite
