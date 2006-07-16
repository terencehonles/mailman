# Copyright (C) 2001-2006 by the Free Software Foundation, Inc.
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
import stat
import shutil
import difflib
import tempfile
import unittest

from cStringIO import StringIO

from Mailman import MailList
from Mailman import Utils
from Mailman.configuration import config

NL = '\n'
PERMISSIONS = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH



class TestBase(unittest.TestCase):
    def _configure(self, fp):
##         print >> fp, \
##               "MEMBER_ADAPTOR_CLASS = 'Mailman.SAMemberships.SAMemberships'"
##         config.MEMBER_ADAPTOR_CLASS = 'Mailman.SAMemberships.SAMemberships'
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
        # Write a temporary configuration file, but allow for subclasses to
        # add additional data.
        fd, self._config = tempfile.mkstemp(suffix='.cfg')
        os.close(fd)
        fp = open(self._config, 'w')
        try:
            self._configure(fp)
        finally:
            fp.close()
        os.chmod(self._config, PERMISSIONS)
        mlist = MailList.MailList()
        mlist.Create('_xtest@example.com', 'owner@example.com', 'xxxxx')
        mlist.Save()
        # We need to reload the mailing list to ensure that the member
        # adaptors are all sync'd up.  This isn't strictly necessary with the
        # OldStyleMemberships adaptor, but it may be required for other
        # adaptors
        mlist.Load()
        # This leaves the list in a locked state
        self._mlist = mlist

    def tearDown(self):
        self._mlist.Unlock()
        listname = self._mlist.fqdn_listname
        for dirtmpl in ['lists/%s',
                        'archives/private/%s',
                        'archives/private/%s.mbox',
                        'archives/public/%s',
                        'archives/public/%s.mbox',
                        ]:
            dir = os.path.join(config.VAR_PREFIX, dirtmpl % listname)
            if os.path.islink(dir):
                os.unlink(dir)
            elif os.path.isdir(dir):
                shutil.rmtree(dir)
        os.unlink(self._config)
