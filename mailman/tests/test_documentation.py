# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Harness for testing Mailman's documentation."""

import os
import doctest
import unittest

from email import message_from_string

import mailman

from mailman.Message import Message
from mailman.app.styles import style_manager
from mailman.configuration import config


DOT = '.'
COMMASPACE = ', '



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


def setup(testobj):
    """Test setup."""
    testobj.globs['message_from_string'] = specialized_message_from_string



def cleaning_teardown(testobj):
    """Clear all persistent data at the end of a doctest."""
    # Clear the database of all rows.
    config.db._reset()
    # Remove all but the default style.
    for style in style_manager.styles:
        if style.name <> 'default':
            style_manager.unregister(style)
    # Remove all queue files.
    for dirpath, dirnames, filenames in os.walk(config.QUEUE_DIR):
        for filename in filenames:
            os.remove(os.path.join(dirpath, filename))
    # Clear out messages in the message store.
    for message in config.db.message_store.messages:
        config.db.message_store.delete_message(message['message-id'])



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
    if config.opts.verbosity <= 2:
        flags |= doctest.REPORT_ONLY_FIRST_FAILURE
    # Add all the doctests in all subpackages.
    for docsdir in packages:
        for filename in os.listdir(os.path.join('mailman', docsdir)):
            if os.path.splitext(filename)[1] == '.txt':
                test = doctest.DocFileSuite(
                    os.path.join(docsdir, filename),
                    package='mailman',
                    optionflags=flags,
                    setUp=setup,
                    tearDown=cleaning_teardown)
                suite.addTest(test)
    return suite
