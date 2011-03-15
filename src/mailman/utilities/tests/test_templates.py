# Copyright (C) 2011 by the Free Software Foundation, Inc.
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

"""Testing i18n template search and interpolation."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'test_suite',
    ]


import os
import shutil
import tempfile
import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.languages import ILanguageManager
from mailman.testing.layers import ConfigLayer
#from mailman.utilities.i18n import find, make

from mailman.Utils import findtext



class TestFind(unittest.TestCase):
    layer = ConfigLayer

    def setUp(self):
        self.template_dir = tempfile.mkdtemp()
        config.push('template config', """\
        [paths.testing]
        template_dir: {0}
        """.format(self.template_dir))
        # The following MUST happen AFTER the push() above since pushing a new
        # config also clears out the language manager.
        getUtility(ILanguageManager).add('xx', 'utf-8', 'Xlandia')
        self.mlist = create_list('test@example.com')
        self.mlist.preferred_language = 'xx'
        # Populate global tempdir with a few fake templates.
        self.xxdir = os.path.join(self.template_dir, 'xx')
        os.mkdir(self.xxdir)
        with open(os.path.join(self.xxdir, 'global.txt'), 'w') as fp:
            print >> fp, 'Global template'
        self.sitedir = os.path.join(self.template_dir, 'site', 'xx')
        os.makedirs(self.sitedir)
        with open(os.path.join(self.sitedir, 'site.txt'), 'w') as fp:
            print >> fp, 'Site template'
        self.domaindir = os.path.join(self.template_dir, 'example.com', 'xx')
        os.makedirs(self.domaindir)
        with open(os.path.join(self.domaindir, 'domain.txt'), 'w') as fp:
            print >> fp, 'Domain template'
        self.listdir = os.path.join(self.mlist.data_path, 'xx')
        os.makedirs(self.listdir)
        with open(os.path.join(self.listdir, 'list.txt'), 'w') as fp:
            print >> fp, 'List template'

    def tearDown(self):
        config.pop('template config')
        shutil.rmtree(self.template_dir)
        shutil.rmtree(self.listdir)

    def test_find_global_template(self):
        text, filename = findtext('global.txt', lang='xx')
        self.assertEqual(text, 'Global template\n')
        self.assertEqual(filename, os.path.join(self.xxdir, 'global.txt'))

    def test_find_site_template(self):
        text, filename = findtext('site.txt', lang='xx')
        self.assertEqual(text, 'Site template\n')
        self.assertEqual(filename, os.path.join(self.sitedir, 'site.txt'))

    def test_find_domain_template(self):
        text, filename = findtext('domain.txt', mlist=self.mlist)
        self.assertEqual(text, 'Domain template\n')
        self.assertEqual(filename, os.path.join(self.domaindir, 'domain.txt'))

    def test_find_list_template(self):
        text, filename = findtext('list.txt', mlist=self.mlist)
        self.assertEqual(text, 'List template\n')
        self.assertEqual(filename, os.path.join(self.listdir, 'list.txt'))



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFind))
    return suite
