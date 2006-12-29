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

"""Mailman unit test driver."""

import os
import re
import sys
import optparse
import unittest

from Mailman import Version
from Mailman import loginit
from Mailman.i18n import _
from Mailman.initialize import initialize

__i18n_templates__ = True



def v_callback(option, opt, value, parser):
    if opt in ('-q', '--quiet'):
        delta = -1
    elif opt in ('-v', '--verbose'):
        delta = 1
    else:
        delta = 0
    dest = getattr(parser.values, option.dest)
    setattr(parser.values, option.dest, max(0, dest + delta))


def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
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
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    return parser, opts, args



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
                testnames.append('Mailman.' + modpath)
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


def suite(patterns=None):
    if patterns is None:
        patterns = '.'
    loader = unittest.TestLoader()
    # Search for all tests that match the given patterns
    testnames = search()
    suite = loader.loadTestsFromNames(testnames)
    return filter_tests(suite, patterns)



def main():
    global basedir

    parser, opts, args = parseargs()
    initialize(opts.config)
    if not args:
        args = ['.']
    loginit.initialize(propagate=opts.stderr)

    import Mailman
    basedir = os.path.dirname(Mailman.__file__)
    runner = unittest.TextTestRunner(verbosity=opts.verbosity)
    results = runner.run(suite(args))
    sys.exit(bool(results.failures or results.errors))



if __name__ == '__main__':
    main()
