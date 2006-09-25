# Copyright (C) 1998-2006 by the Free Software Foundation, Inc.
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

import optparse

from Mailman import Version
from Mailman.i18n import _

__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog

Print the Mailman version and exit."""))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    # Yes, this is kind of silly
    print _('Using Mailman version: $Version.MAILMAN_VERSION')



if __name__ == '__main__':
    main()
