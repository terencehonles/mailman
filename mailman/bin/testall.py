# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
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

"""Mailman unit test driver."""

from __future__ import with_statement

import os
import re
import grp
import pwd
import sys
import random
import shutil
import optparse
import tempfile
import unittest
import pkg_resources

from mailman import Defaults
from mailman.configuration import config
from mailman.i18n import _
from mailman.initialize import initialize_1, initialize_2, initialize_3
from mailman.testing.helpers import SMTPServer
from mailman.version import MAILMAN_VERSION


basedir = None



def v_callback(option, opt, value, parser):
    if opt in ('-q', '--quiet'):
        delta = -1
    elif opt in ('-v', '--verbose'):
        delta = 1
    else:
        raise AssertionError('Unexpected option: %s' % opt)
    dest = getattr(parser.values, option.dest)
    setattr(parser.values, option.dest, max(0, dest + delta))


def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] [tests]

Run the Mailman unit test suite.  'tests' is one or more Python regular
expressions matching only the tests you want to run.  Prefix the regular
expression with '!' to specify a negative test."""))
    parser.set_defaults(verbosity=2)
    parser.add_option('-v', '--verbose',
                      action='callback', callback=v_callback,
                      dest='verbosity', help=_("""\
Increase verbosity by 1, which defaults to %default.  Use -q to reduce
verbosity.  -v and -q options accumulate."""))
    parser.add_option('-q', '--quiet',
                      action='callback', callback=v_callback,
                      dest='verbosity', help=_("""\
Reduce verbosity by 1 (but not below 0)."""))
    parser.add_option('-e', '--stderr',
                      default=False, action='store_true',
                      help=_('Propagate log errors to stderr.'))
    parser.add_option('-c', '--coverage',
                      default=False, action='store_true',
                      help=_('Enable code coverage.'))
    parser.add_option('-r', '--randomize',
                      default=False, action='store_true',
                      help=_("""\
Randomize the tests; good for finding subtle dependency errors.  Note that
this isn't completely random though because the doctests are not mixed with
the Python tests.  Each type of test is randomized within its group."""))
    options, arguments = parser.parse_args()
    if len(arguments) == 0:
        arguments = ['.']
    parser.options = options
    parser.arguments = arguments
    return parser



def search():
    testnames = []
    # Walk the entire tree from the current base directory.  Look for modules
    # that start with 'test_'.  Calculate the full module path name to this
    # module, append 'test_suite' and add that to testnames.  This way, we run
    # all the suites defined in the test_suite() function inside all test
    # modules.
    for dirpath, dirnames, filenames in os.walk(basedir):
        for fn in filenames:
            if fn.startswith('test_') and fn.endswith('.py'):
                # Start with full path
                path = os.path.join(dirpath, fn)
                # Convert the file path to a module path.  First, we must make
                # the file path relative to the root directory.  Then strip
                # off the trailing .py
                path = path[len(basedir)+1:-3]
                # Convert slashes to dots
                modpath = path.replace(os.sep, '.') + '.test_suite'
                testnames.append('mailman.' + modpath)
    return testnames


def match(pat, name):
    if not pat:
        return True
    if pat.startswith('!'):
        # Negative test
        return re.search(pat[1:], name) is None
    else:
        # Positive test
        return re.search(pat, name) is not None


def filter_tests(suite, patterns):
    if '.' in patterns:
        return suite
    new = unittest.TestSuite()
    for test in suite._tests:
        if isinstance(test, unittest.TestCase):
            # Get the fill test name: package.module.class.method
            name = test.id()
            for pat in patterns:
                if match(pat, name):
                    new.addTest(test)
                    break
        else:
            filtered = filter_tests(test, patterns)
            if filtered:
                new.addTest(filtered)
    return new


def suite(patterns, randomize):
    if patterns is None:
        patterns = '.'
    loader = unittest.TestLoader()
    # Search for all tests that match the given patterns
    testnames = search()
    suite = loader.loadTestsFromNames(testnames)
    tests = filter_tests(suite, patterns)
    if randomize:
        random.shuffle(tests._tests)
    else:
        tests._tests.sort()
    return tests



def main():
    global basedir

    parser = parseargs()

    # Set verbosity level for test_documentation.py.  XXX There should be a
    # better way to do this.
    class Bag: pass
    config.tests = Bag()
    config.tests.verbosity = parser.options.verbosity
    config.tests.randomize = parser.options.randomize

    # Turn on code coverage if selected.
    if parser.options.coverage:
        try:
            import coverage
        except ImportError:
            parser.options.coverage = False
        else:
            coverage.start()

    # Set up the testing configuration file both for this process, and for all
    # sub-processes testing will spawn (e.g. the qrunners).
    #
    # Also create a logging.cfg file with values reflecting verbosity and
    # stderr propagation.  Enable it only if necessary.
    fd, logging_cfg = tempfile.mkstemp(suffix='.cfg')
    os.close(fd)
    enable_logging_cfg = False
    with open(logging_cfg, 'w') as fp:
        print >> fp, '[*]'
        if parser.options.stderr:
            print >> fp, 'propagate = True'
            enable_logging_cfg = True
        if parser.options.verbosity > 2:
            print >> fp, 'level = DEBUG'
            enable_logging_cfg = True

    cfg_in = pkg_resources.resource_string(
        'mailman.testing', 'testing.cfg.in')
    fd, cfg_out = tempfile.mkstemp(suffix='.cfg')
    os.close(fd)
    with open(cfg_out, 'w') as fp:
        fp.write(cfg_in)
        if enable_logging_cfg:
            print >> fp, 'LOG_CONFIG_FILE = "%s"' % logging_cfg

    # Calculate a temporary VAR_DIR directory so that run-time artifacts of
    # the tests won't tread on the installation's data.  This also makes it
    # easier to clean up after the tests are done, and insures isolation of
    # test suite runs.
    var_dir = tempfile.mkdtemp()
    if parser.options.verbosity > 2:
        print 'VAR_DIR :', var_dir
        print 'config file:', cfg_out
        if enable_logging_cfg:
            print 'logging config file:', logging_cfg

    user_id = os.getuid()
    user_name = pwd.getpwuid(user_id).pw_name
    group_id = os.getgid()
    group_name = grp.getgrgid(group_id).gr_name

    try:
        with open(cfg_out, 'a') as fp:
            print >> fp, 'VAR_DIR = "%s"' % var_dir
            print >> fp, 'MAILMAN_USER = "%s"' % user_name
            print >> fp, 'MAILMAN_UID =', user_id
            print >> fp, 'MAILMAN_GROUP = "%s"' % group_name
            print >> fp, 'MAILMAN_GID =', group_id
            print >> fp, "LANGUAGES = 'en'"
            print >> fp, 'SMTPPORT =', SMTPServer.port
            # A fake MHonArc command, for testing.
            print >> fp, 'MHONARC_COMMAND = """/bin/echo', \
                  Defaults.MHONARC_COMMAND, '"""'

        initialize_1(cfg_out, propagate_logs=parser.options.stderr)
        mailman_uid = pwd.getpwnam(config.MAILMAN_USER).pw_uid
        mailman_gid = grp.getgrnam(config.MAILMAN_GROUP).gr_gid
        os.chmod(cfg_out, 0660)
        os.chown(cfg_out, mailman_uid, mailman_gid)

        # Create an empty SQLite database file with the proper permissions and
        # calculate the SQLAlchemy engine url to this database file.
        fd, config.dbfile = tempfile.mkstemp(dir=config.DATA_DIR, suffix='.db')
        os.close(fd)
        os.chmod(config.dbfile, 0660)
        os.chown(config.dbfile, mailman_uid, mailman_gid)

        # Patch ups.
        test_engine_url = 'sqlite:///' + config.dbfile
        config.DEFAULT_DATABASE_URL = test_engine_url

        # Write this to the config file so subprocesses share the same testing
        # database file.
        with open(cfg_out, 'a') as fp:
            print >> fp, 'DEFAULT_DATABASE_URL = "%s"' % test_engine_url

        # With -vvv, turn on engine debugging.
        initialize_2(parser.options.verbosity > 3)
        initialize_3()

        # Run the tests.  XXX I'm not sure if basedir can be converted to
        # pkg_resources.
        import mailman
        basedir = os.path.dirname(mailman.__file__)
        runner = unittest.TextTestRunner(verbosity=parser.options.verbosity)
        results = runner.run(suite(parser.arguments, parser.options.randomize))
    finally:
        os.remove(cfg_out)
        os.remove(logging_cfg)
        shutil.rmtree(var_dir)

    # Turn off coverage and print a report
    if parser.options.coverage:
        coverage.stop()
        modules = [module for name, module in sys.modules.items()
                   if module
                   and name is not None
                   and name.split('.')[0] == 'mailman']
        coverage.report(modules)
    sys.exit(bool(results.failures or results.errors))



if __name__ == '__main__':
    main()
