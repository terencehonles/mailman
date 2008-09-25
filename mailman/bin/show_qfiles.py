# Copyright (C) 2006-2008 by the Free Software Foundation, Inc.
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

import sys
import optparse
from cPickle import load

from mailman.configuration import config
from mailman.i18n import _
from mailman.version import MAILMAN_VERSION



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
