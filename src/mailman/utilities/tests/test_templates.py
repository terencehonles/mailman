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
from mailman.utilities.i18n import TemplateNotFoundError, _search, find, make



class TestSearchOrder(unittest.TestCase):
    """Test internal search order for language templates."""

    layer = ConfigLayer

    def setUp(self):
        self.template_dir = tempfile.mkdtemp()
        config.push('no template dir', """\
        [mailman]
        default_language: fr
        [paths.testing]
        template_dir: {0}/t
        var_dir: {0}/v
        """.format(self.template_dir))
        language_manager = getUtility(ILanguageManager)
        language_manager.add('de', 'utf-8', 'German')
        language_manager.add('it', 'utf-8', 'Italian')
        self.mlist = create_list('l@example.com')
        self.mlist.preferred_language = 'de'

    def tearDown(self):
        config.pop('no template dir')
        shutil.rmtree(self.template_dir)

    def _stripped_search_order(self, template_file,
                               mailing_list=None, language=None):
        raw_search_order = _search(template_file, mailing_list, language)
        for path in raw_search_order:
            yield path[len(self.template_dir):]

    def test_fully_specified_search_order(self):
        search_order = self._stripped_search_order('foo.txt', self.mlist, 'it')
        # language argument
        self.assertEqual(next(search_order),
                         '/v/lists/l@example.com/it/foo.txt')
        self.assertEqual(next(search_order), '/t/example.com/it/foo.txt')
        self.assertEqual(next(search_order), '/t/site/it/foo.txt')
        self.assertEqual(next(search_order), '/t/it/foo.txt')
        # mlist.preferred_language
        self.assertEqual(next(search_order),
                         '/v/lists/l@example.com/de/foo.txt')
        self.assertEqual(next(search_order), '/t/example.com/de/foo.txt')
        self.assertEqual(next(search_order), '/t/site/de/foo.txt')
        self.assertEqual(next(search_order), '/t/de/foo.txt')
        # site's default language
        self.assertEqual(next(search_order),
                         '/v/lists/l@example.com/fr/foo.txt')
        self.assertEqual(next(search_order), '/t/example.com/fr/foo.txt')
        self.assertEqual(next(search_order), '/t/site/fr/foo.txt')
        self.assertEqual(next(search_order), '/t/fr/foo.txt')
        # English
        self.assertEqual(next(search_order),
                         '/v/lists/l@example.com/en/foo.txt')
        self.assertEqual(next(search_order), '/t/example.com/en/foo.txt')
        self.assertEqual(next(search_order), '/t/site/en/foo.txt')
        self.assertEqual(next(search_order), '/t/en/foo.txt')

    def test_no_language_argument_search_order(self):
        search_order = self._stripped_search_order('foo.txt', self.mlist)
        # mlist.preferred_language
        self.assertEqual(next(search_order),
                         '/v/lists/l@example.com/de/foo.txt')
        self.assertEqual(next(search_order), '/t/example.com/de/foo.txt')
        self.assertEqual(next(search_order), '/t/site/de/foo.txt')
        self.assertEqual(next(search_order), '/t/de/foo.txt')
        # site's default language
        self.assertEqual(next(search_order),
                         '/v/lists/l@example.com/fr/foo.txt')
        self.assertEqual(next(search_order), '/t/example.com/fr/foo.txt')
        self.assertEqual(next(search_order), '/t/site/fr/foo.txt')
        self.assertEqual(next(search_order), '/t/fr/foo.txt')
        # English
        self.assertEqual(next(search_order),
                         '/v/lists/l@example.com/en/foo.txt')
        self.assertEqual(next(search_order), '/t/example.com/en/foo.txt')
        self.assertEqual(next(search_order), '/t/site/en/foo.txt')
        self.assertEqual(next(search_order), '/t/en/foo.txt')

    def test_no_mailing_list_argument_search_order(self):
        search_order = self._stripped_search_order('foo.txt', language='it')
        # language argument
        self.assertEqual(next(search_order), '/t/site/it/foo.txt')
        self.assertEqual(next(search_order), '/t/it/foo.txt')
        # site's default language
        self.assertEqual(next(search_order), '/t/site/fr/foo.txt')
        self.assertEqual(next(search_order), '/t/fr/foo.txt')
        # English
        self.assertEqual(next(search_order), '/t/site/en/foo.txt')
        self.assertEqual(next(search_order), '/t/en/foo.txt')

    def test_no_optional_arguments_search_order(self):
        search_order = self._stripped_search_order('foo.txt')
        # site's default language
        self.assertEqual(next(search_order), '/t/site/fr/foo.txt')
        self.assertEqual(next(search_order), '/t/fr/foo.txt')
        # English
        self.assertEqual(next(search_order), '/t/site/en/foo.txt')
        self.assertEqual(next(search_order), '/t/en/foo.txt')



class TestFind(unittest.TestCase):
    """Test template search."""

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
        self.fp = None
        # Populate global tempdir with a few fake templates.
        self.xxdir = os.path.join(self.template_dir, 'xx')
        os.mkdir(self.xxdir)
        with open(os.path.join(self.xxdir, 'global.txt'), 'w') as fp:
            fp.write('Global template')
        self.sitedir = os.path.join(self.template_dir, 'site', 'xx')
        os.makedirs(self.sitedir)
        with open(os.path.join(self.sitedir, 'site.txt'), 'w') as fp:
            fp.write('Site template')
        self.domaindir = os.path.join(self.template_dir, 'example.com', 'xx')
        os.makedirs(self.domaindir)
        with open(os.path.join(self.domaindir, 'domain.txt'), 'w') as fp:
            fp.write('Domain template')
        self.listdir = os.path.join(self.mlist.data_path, 'xx')
        os.makedirs(self.listdir)
        with open(os.path.join(self.listdir, 'list.txt'), 'w') as fp:
            fp.write('List template')

    def tearDown(self):
        if self.fp is not None:
            self.fp.close()
        config.pop('template config')
        shutil.rmtree(self.template_dir)
        shutil.rmtree(self.listdir)

    def test_find_global_template(self):
        filename, self.fp = find('global.txt', language='xx')
        self.assertEqual(filename, os.path.join(self.xxdir, 'global.txt'))
        self.assertEqual(self.fp.read(), 'Global template')

    def test_find_site_template(self):
        filename, self.fp = find('site.txt', language='xx')
        self.assertEqual(filename, os.path.join(self.sitedir, 'site.txt'))
        self.assertEqual(self.fp.read(), 'Site template')

    def test_find_domain_template(self):
        filename, self.fp = find('domain.txt', self.mlist)
        self.assertEqual(filename, os.path.join(self.domaindir, 'domain.txt'))
        self.assertEqual(self.fp.read(), 'Domain template')

    def test_find_list_template(self):
        filename, self.fp = find('list.txt', self.mlist)
        self.assertEqual(filename, os.path.join(self.listdir, 'list.txt'))
        self.assertEqual(self.fp.read(), 'List template')

    def test_template_not_found(self):
        # Python 2.6 compatibility.
        try:
            find('missing.txt', self.mlist)
        except TemplateNotFoundError as error:
            self.assertEqual(error.template_file, 'missing.txt')
        else:
            raise AssertionError('TemplateNotFoundError expected')



class TestMake(unittest.TestCase):
    """Test template interpolation."""

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
        # Populate the template directory with some samples.
        self.xxdir = os.path.join(self.template_dir, 'xx')
        os.mkdir(self.xxdir)
        with open(os.path.join(self.xxdir, 'nosub.txt'), 'w') as fp:
            print >> fp, """\
This is a global template.
It has no substitutions.
It will be wrapped.
"""
        with open(os.path.join(self.xxdir, 'subs.txt'), 'w') as fp:
            print >> fp, """\
This is a $kind template.
It has $howmany substitutions.
It will be wrapped.
"""
        with open(os.path.join(self.xxdir, 'nowrap.txt'), 'w') as fp:
            print >> fp, """\
This is a $kind template.
It has $howmany substitutions.
It will not be wrapped.
"""

    def tearDown(self):
        config.pop('template config')
        shutil.rmtree(self.template_dir)

    def test_no_substitutions(self):
        self.assertEqual(make('nosub.txt', self.mlist), """\
This is a global template.  It has no substitutions.  It will be
wrapped.""")

    def test_substitutions(self):
        self.assertEqual(make('subs.txt', self.mlist,
                              kind='very nice',
                              howmany='a few'), """\
This is a very nice template.  It has a few substitutions.  It will be
wrapped.""")

    def test_substitutions_no_wrap(self):
        self.assertEqual(make('nowrap.txt', self.mlist, wrap=False,
                              kind='very nice',
                              howmany='a few'), """\
This is a very nice template.
It has a few substitutions.
It will not be wrapped.
""")



def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSearchOrder))
    suite.addTest(unittest.makeSuite(TestFind))
    suite.addTest(unittest.makeSuite(TestMake))
    return suite
