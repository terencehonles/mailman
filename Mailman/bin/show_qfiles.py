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

import sys
import optparse
from cPickle import load

from Mailman import Version
from Mailman.configuration import config
from Mailman.i18n import _

__i18_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%%prog [options] qfiles ...

Show the contents of one or more Mailman queue files."""))
    parser.add_option('-q', '--quiet',
                      default=False, action='store_true',
                      help=_("Don't print 'helpful' message delimiters."))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    config.load(opts.config)

    for filename in args:
        if not opts.quiet:
            print '====================>', filename
        fp = open(filename)
        if filename.endswith(".pck"):
            msg = load(fp)
            data = load(fp)
            if data.get('_parsemsg'):
                sys.stdout.write(msg)
            else:
                sys.stdout.write(msg.as_string())
        else:
            sys.stdout.write(fp.read())



if __name__ == '__main__':
    main()
