# Copyright (C) 2006 by the Free Software Foundation, Inc.
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

import re
import sys
import pprint
import optparse

from Mailman import mm_cfg
from Mailman.i18n import _

__i18_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=mm_cfg.MAILMAN_VERSION,
                                   usage=_("""\
%%prog [options] [pattern ...]

Show the values of various Defaults.py/mm_cfg.py variables.
If one or more patterns are given, show only those variables
whose names match a pattern"""))
    parser.add_option('-v', '--verbose',
                      default=False, action='store_true',
                      help=_("Show all mm_cfg names, not just 'settings'."))
    parser.add_option('-i', '--ignorecase',
                      default=False, action='store_true',
                      help=_("Match patterns case-insensitively."))
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
    names = mm_cfg.__dict__.keys()
    names.sort()
    for name in names:
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
        value = mm_cfg.__dict__[name]
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
