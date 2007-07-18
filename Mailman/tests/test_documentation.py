# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

import Mailman
from Mailman.configuration import config
from Mailman.database import flush


COMMASPACE = ', '



def cleaning_teardown(testobj):
    # Remove all users, addresses and members, then delete all mailing lists.
    for user in config.user_manager.users:
        config.user_manager.delete_user(user)
    for address in config.user_manager.addresses:
        config.user_manager.delete_address(address)
    for mlist in config.list_manager.mailing_lists:
        for member in mlist.members.members:
            member.unsubscribe()
        for admin in mlist.administrators.members:
            admin.unsubscribe()
        config.list_manager.delete(mlist)
    flush()
    assert not list(config.list_manager.mailing_lists), (
        'There should be no mailing lists left: %s' %
        COMMASPACE.join(sorted(config.list_manager.names)))
    assert not list(config.user_manager.users), (
        'There should be no users left!')
    assert not list(config.user_manager.addresses), (
        'There should be no addresses left!')
    # Remove all queue files.
    for dirpath, dirnames, filenames in os.walk(config.QUEUE_DIR):
        for filename in filenames:
            os.remove(os.path.join(dirpath, filename))



def test_suite():
    suite = unittest.TestSuite()
    docsdir = os.path.join(os.path.dirname(Mailman.__file__), 'docs')
    # Under higher verbosity settings, report all doctest errors, not just the
    # first one.
    flags = (doctest.ELLIPSIS |
             doctest.NORMALIZE_WHITESPACE |
             doctest.REPORT_NDIFF)
    if config.opts.verbosity <= 2:
        flags |= doctest.REPORT_ONLY_FIRST_FAILURE
    for filename in os.listdir(docsdir):
        if os.path.splitext(filename)[1] == '.txt':
            test = doctest.DocFileSuite(
                'docs/' + filename,
                package=Mailman,
                optionflags=flags,
                tearDown=cleaning_teardown)
            suite.addTest(test)
    return suite
