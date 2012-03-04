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

"""Test the template downloader API."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TestTemplateLoader',
    ]


import os
import shutil
import urllib2
import tempfile
import unittest

from zope.component import getUtility

from mailman.app.lifecycle import create_list
from mailman.config import config
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.templates import ITemplateLoader
from mailman.testing.layers import ConfigLayer



class TestTemplateLoader(unittest.TestCase):
    """Test the template downloader API."""

    layer = ConfigLayer

    def setUp(self):
        self.var_dir = tempfile.mkdtemp()
        config.push('template config', """\
        [paths.testing]
        var_dir: {0}
        """.format(self.var_dir))
        # Put a demo template in the site directory.
        path = os.path.join(self.var_dir, 'templates', 'site', 'en')
        os.makedirs(path)
        with open(os.path.join(path, 'demo.txt'), 'w') as fp:
            print('Test content', end='', file=fp)
        self._loader = getUtility(ITemplateLoader)
        getUtility(ILanguageManager).add('it', 'utf-8', 'Italian')
        self._mlist = create_list('test@example.com')

    def tearDown(self):
        config.pop('template config')
        shutil.rmtree(self.var_dir)

    def test_mailman_internal_uris(self):
        # mailman://demo.txt
        content = self._loader.get('mailman:///demo.txt')
        self.assertEqual(content, 'Test content')

    def test_mailman_internal_uris_twice(self):
        # mailman:///demo.txt
        content = self._loader.get('mailman:///demo.txt')
        self.assertEqual(content, 'Test content')
        content = self._loader.get('mailman:///demo.txt')
        self.assertEqual(content, 'Test content')

    def test_mailman_uri_with_language(self):
        content = self._loader.get('mailman:///en/demo.txt')
        self.assertEqual(content, 'Test content')

    def test_mailman_uri_with_english_fallback(self):
        content = self._loader.get('mailman:///it/demo.txt')
        self.assertEqual(content, 'Test content')

    def test_mailman_uri_with_list_name(self):
        content = self._loader.get('mailman:///test@example.com/demo.txt')
        self.assertEqual(content, 'Test content')

    def test_mailman_full_uri(self):
        content = self._loader.get('mailman:///test@example.com/en/demo.txt')
        self.assertEqual(content, 'Test content')

    def test_mailman_full_uri_with_english_fallback(self):
        content = self._loader.get('mailman:///test@example.com/it/demo.txt')
        self.assertEqual(content, 'Test content')

    def test_uri_not_found(self):
        try:
            self._loader.get('mailman:///missing.txt')
        except urllib2.URLError as error:
            self.assertEqual(error.reason, 'No such file')
        else:
            raise AssertionError('Exception expected')

    def test_shorter_url_error(self):
        try:
            self._loader.get('mailman:///')
        except urllib2.URLError as error:
            self.assertEqual(error.reason, 'No template specified')
        else:
            raise AssertionError('Exception expected')

    def test_short_url_error(self):
        try:
            self._loader.get('mailman://')
        except urllib2.URLError as error:
            self.assertEqual(error.reason, 'No template specified')
        else:
            raise AssertionError('Exception expected')

    def test_bad_language(self):
        try:
            self._loader.get('mailman:///xx/demo.txt')
        except urllib2.URLError as error:
            self.assertEqual(error.reason, 'Bad language or list name')
        else:
            raise AssertionError('Exception expected')

    def test_bad_mailing_list(self):
        try:
            self._loader.get('mailman:///missing@example.com/demo.txt')
        except urllib2.URLError as error:
            self.assertEqual(error.reason, 'Bad language or list name')
        else:
            raise AssertionError('Exception expected')

    def test_too_many_path_components(self):
        try:
            self._loader.get('mailman:///missing@example.com/en/foo/demo.txt')
        except urllib2.URLError as error:
            self.assertEqual(error.reason, 'No such file')
        else:
            raise AssertionError('Exception expected')
