# Copyright (C) 2001-2007 by the Free Software Foundation, Inc.
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

"""Test base class which handles creating and deleting a test list."""

import os
import grp
import new
import pwd
import sys
import stat
import shutil
import difflib
import tempfile
import unittest

from cStringIO import StringIO
from sqlalchemy.orm import clear_mappers

from Mailman import MailList
from Mailman import Utils
from Mailman.bin import rmlist
from Mailman.configuration import config
from Mailman.database.dbcontext import dbcontext

NL = '\n'



class TestBase(unittest.TestCase):
    def ndiffAssertEqual(self, first, second):
        """Like failUnlessEqual except use ndiff for readable output."""
        if first <> second:
            sfirst = str(first)
            ssecond = str(second)
            diff = difflib.ndiff(sfirst.splitlines(), ssecond.splitlines())
            fp = StringIO()
            print >> fp, NL, NL.join(diff)
            raise self.failureException(fp.getvalue())

    def setUp(self):
        # Be sure to close the connection to the current database, and then
        # reconnect to the new temporary SQLite database.  Otherwise we end up
        # with turds in the main database and our qrunner subprocesses won't
        # find the mailing list.  Because our global config object's
        # SQLALCHEMY_ENGINE_URL variable has already been updated, the
        # connect() call will open the database file the qrunners will be
        # rendezvousing on.
        dbcontext.close()
        clear_mappers()
        dbcontext.connect()
        mlist = MailList.MailList()
        mlist.Create('_xtest@example.com', 'owner@example.com', 'xxxxx')
        mlist.Save()
        # This leaves the list in a locked state
        self._mlist = mlist

    def tearDown(self):
        self._mlist.Unlock()
        rmlist.delete_list(self._mlist.fqdn_listname, self._mlist,
                           archives=True, quiet=True)
        # Clear out any site locks, which can be left over if tests fail.
        for filename in os.listdir(config.LOCK_DIR):
            if filename.startswith('<site>'):
                path = os.path.join(config.LOCK_DIR, filename)
                print >> sys.stderr, '@@@@@ removing:', path
                os.unlink(path)
