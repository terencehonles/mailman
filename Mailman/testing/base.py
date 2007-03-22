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



def dummy_mta_function(*args, **kws):
    pass



class TestBase(unittest.TestCase):
    def _configure(self, fp):
        # Make sure that we don't pollute the real database with our test
        # mailing list.
        test_engine_url = 'sqlite:///' + self._dbfile
        print >> fp, 'SQLALCHEMY_ENGINE_URL = "%s"' % test_engine_url
        config.SQLALCHEMY_ENGINE_URL = test_engine_url
        # Use the Mailman.MTA.stub module
        print >> fp, 'MTA = "stub"'
        config.MTA = 'stub'
        print >> fp, 'add_domain("example.com", "www.example.com")'
        # Only add this domain once to the current process
        if 'example.com' not in config.domains:
            config.add_domain('example.com', 'www.example.com')

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
        mailman_uid = pwd.getpwnam(config.MAILMAN_USER).pw_uid
        mailman_gid = grp.getgrnam(config.MAILMAN_GROUP).gr_gid
        # Write a temporary configuration file, but allow for subclasses to
        # add additional data.  Make sure the config and db files, which
        # mkstemp creates, has the proper ownership and permissions.
        fd, self._config = tempfile.mkstemp(dir=config.DATA_DIR, suffix='.cfg')
        os.close(fd)
        os.chmod(self._config, 0440)
        os.chown(self._config, mailman_uid, mailman_gid)
        fd, self._dbfile = tempfile.mkstemp(dir=config.DATA_DIR, suffix='.db')
        os.close(fd)
        os.chmod(self._dbfile, 0660)
        os.chown(self._dbfile, mailman_uid, mailman_gid)
        fp = open(self._config, 'w')
        try:
            self._configure(fp)
        finally:
            fp.close()
        # Create a fake new Mailman.MTA module which stubs out the create()
        # and remove() functions.
        stubmta_module = new.module('Mailman.MTA.stub')
        sys.modules['Mailman.MTA.stub'] = stubmta_module
        stubmta_module.create = dummy_mta_function
        stubmta_module.remove = dummy_mta_function
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
        os.unlink(self._config)
        os.unlink(self._dbfile)
        # Clear out any site locks, which can be left over if tests fail.
        for filename in os.listdir(config.LOCK_DIR):
            if filename.startswith('<site>'):
                path = os.path.join(config.LOCK_DIR, filename)
                print >> sys.stderr, '@@@@@ removing:', path
                os.unlink(path)
