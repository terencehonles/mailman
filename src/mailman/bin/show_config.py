# Copyright (C) 2006-2012 by the Free Software Foundation, Inc.
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

import re
import sys
import pprint
import optparse

from mailman.configuration import config
from mailman.core.i18n import _
from mailman.version import MAILMAN_VERSION


# List of names never to show even if --verbose
NEVER_SHOW = ['__builtins__', '__doc__']



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%%prog [options] [pattern ...]

Show the values of various Defaults.py/mailman.cfg variables.
If one or more patterns are given, show only those variables
whose names match a pattern"""))
    parser.add_option('-v', '--verbose',
                      default=False, action='store_true',
                      help=_(
"Show all configuration names, not just 'settings'."))
    parser.add_option('-i', '--ignorecase',
                      default=False, action='store_true',
                      help=_("Match patterns case-insensitively."))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    return parser, opts, args



def main():
    parser, opts, args = parseargs()

    patterns = []
    if opts.ignorecase:
        flag = re.IGNORECASE
    else:
        flag = 0
    for pattern in args:
        patterns.append(re.compile(pattern, flag))

    pp = pprint.PrettyPrinter(indent=4)
    config.load(opts.config)
    names = config.__dict__.keys()
    names.sort()
    for name in names:
        if name in NEVER_SHOW:
            continue
        if not opts.verbose:
            if name.startswith('_') or re.search('[a-z]', name):
                continue
        if patterns:
            hit = False
            for pattern in patterns:
                if pattern.search(name):
                    hit = True
                    break
            if not hit:
                continue
        value = config.__dict__[name]
        if isinstance(value, str):
            if re.search('\n', value):
                print '%s = """%s"""' %(name, value)
            else:
                print "%s = '%s'" % (name, value)
        else:
            print '%s = ' % name,
            pp.pprint(value)



if __name__ == '__main__':
    main()
