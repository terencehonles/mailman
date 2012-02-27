# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""Test configuration file searching."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import os
import sys
import shutil
import tempfile
import unittest

from contextlib import contextmanager

from mailman.core.initialize import search_for_configuration_file



# Here are a couple of context managers that make our tests easier to read.
@contextmanager
def fakedirs(path):
    """Create and clean up a directory hierarchy."""
    os.makedirs(path)
    try:
        yield
    finally:
        shutil.rmtree(path)


@contextmanager
def hackenv(envar, new_value):
    """Hack the environment temporarily, then reset it."""
    old_value = os.getenv(envar)
    os.environ[envar] = new_value
    try:
        yield
    finally:
        if old_value is None:
            del os.environ[envar]
        else:
            os.environ[envar] = old_value


@contextmanager
def chdir(new_cwd):
    """Change to the directory, then back again."""
    old_cwd = os.getcwd()
    os.chdir(new_cwd)
    try:
        yield
    finally:
        os.chdir(old_cwd)


@contextmanager
def argv0(new_argv0):
    """Change argv0, then back again."""
    old_argv0 = sys.argv[0]
    sys.argv[0] = new_argv0
    try:
        yield
    finally:
        sys.argv[0] = old_argv0



class TestConfigFileBase(unittest.TestCase):
    """Common test infrastructure."""

    def setUp(self):
        self._root = tempfile.mkdtemp()
        # Ensure that the environment can't cause test failures.
        self.mailman_config_file = os.environ.get('MAILMAN_CONFIG_FILE')
        if self.mailman_config_file is not None:
            del os.environ['MAILMAN_CONFIG_FILE']

    def tearDown(self):
        shutil.rmtree(self._root)
        # Restore the environment, though I'm not actually sure this is
        # necessary.
        if self.mailman_config_file is not None:
            os.environ['MAILMAN_CONFIG_FILE'] = self.mailman_config_file

    def _make_fake(self, path):
        if path.startswith('/'):
            path = path[1:]
        return os.path.join(self._root, path)


class TestConfigFileSearch(TestConfigFileBase):
    """Test various aspects of searching for configuration files.

    Note that the command line -C option is not tested here.
    """

    def test_current_working_directory(self):
        fake_cwd = '/home/alex/mailman/hacking'
        fake_testdir = self._make_fake(fake_cwd)
        config_file = os.path.realpath(
            os.path.join(fake_testdir, 'mailman.cfg'))
        with fakedirs(fake_testdir):
            # Write a mostly empty configuration file.
            with open(os.path.join(fake_testdir, 'mailman.cfg'), 'w') as fp:
                print >> fp, '# Fake mailman.cfg file'
            with chdir(fake_testdir):
                # Sometimes symlinks bite us (eg. OS X /var -> /private/var).
                found = os.path.realpath(search_for_configuration_file())
                self.assertEqual(found, config_file)


class TestConfigFileSearchWithChroot(TestConfigFileBase):
    """Like `TestConfigFileSearch` but with a special os.path.exists()."""

    def setUp(self):
        TestConfigFileBase.setUp(self)
        # We can't actually call os.chroot() unless we're root.  Neither can
        # we write to say /etc/mailman.cfg without being root (of course we
        # wouldn't want to even if we could).  The easiest way to fake a file
        # system that we can write to and test is to hack os.path.exists() to
        # prepend a temporary directory onto the path it tests.
        self._os_path_exists = os.path.exists
        def exists(path):
            # Strip off the leading slash, otherwise we'll end up with path.
            return self._os_path_exists(self._make_fake(path))
        os.path.exists = exists

    def tearDown(self):
        os.path.exists = self._os_path_exists
        TestConfigFileBase.tearDown(self)

    def test_baseline(self):
        # With nothing set, and no configuration files, just return None.
        self.assertEqual(search_for_configuration_file(), None)

    def test_environment_variable_to_missing_path(self):
        # Test that $MAILMAN_CONFIG_FILE pointing to a non-existent path still
        # returns None.
        with hackenv('MAILMAN_CONFIG_FILE', '/does/not/exist'):
            self.assertEqual(search_for_configuration_file(), None)

    def test_environment_variable(self):
        # Test that $MAILMAN_CONFIG_FILE pointing to an existing path returns
        # that path.
        fake_home = '/home/geddy/testing/mailman'
        fake_testdir = self._make_fake(fake_home)
        config_file = os.path.join(fake_home, 'mailman.cfg')
        with fakedirs(fake_testdir):
            # Write a mostly empty configuration file.
            with open(os.path.join(fake_testdir, 'mailman.cfg'), 'w') as fp:
                print >> fp, '# Fake mailman.cfg file'
            with hackenv('MAILMAN_CONFIG_FILE', config_file):
                self.assertEqual(search_for_configuration_file(), config_file)

    def test_home_dot_file(self):
        # Test ~/.mailman.cfg
        fake_home = '/home/neil'
        fake_testdir = self._make_fake(fake_home)
        config_file = os.path.join(fake_home, '.mailman.cfg')
        with fakedirs(fake_testdir):
            # Write a mostly empty configuration file.
            with open(os.path.join(fake_testdir, '.mailman.cfg'), 'w') as fp:
                print >> fp, '# Fake mailman.cfg file'
            with hackenv('HOME', '/home/neil'):
                self.assertEqual(search_for_configuration_file(), config_file)

    def test_etc_file(self):
        # Test /etc/mailman.cfg
        fake_etc = '/etc'
        fake_testdir = self._make_fake(fake_etc)
        config_file = os.path.join(fake_etc, 'mailman.cfg')
        with fakedirs(fake_testdir):
            # Write a mostly empty configuration file.
            with open(os.path.join(fake_testdir, 'mailman.cfg'), 'w') as fp:
                print >> fp, '# Fake mailman.cfg file'
            self.assertEqual(search_for_configuration_file(), config_file)

    def test_sibling_directory(self):
        # Test $argv0/../../etc/mailman.cfg
        fake_root = '/usr/local/mm3'
        fake_testdir = self._make_fake(fake_root)
        config_file = os.path.join(fake_testdir, 'etc', 'mailman.cfg')
        fake_config_file = os.path.join(fake_root, 'etc', 'mailman.cfg')
        fake_argv0 = os.path.join(fake_root, 'bin', 'mailman')
        with fakedirs(fake_testdir):
            with argv0(fake_argv0):
                os.mkdir(os.path.dirname(config_file))
                # Write a mostly empty configuration file.
                with open(config_file, 'w') as fp:
                    print >> fp, '# Fake mailman.cfg file'
                self.assertEqual(search_for_configuration_file(), 
                                 fake_config_file)
