# Copyright (C) 1998-2009 by the Free Software Foundation, Inc.
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

import optparse

from mailman import version
from mailman.i18n import _



def parseargs():
    parser = optparse.OptionParser(version=version.MAILMAN_VERSION,
                                   usage=_("""\
%prog

Print the Mailman version and exit."""))
    opts, args = parser.parse_args()
    if args:
        parser.error(_('Unexpected arguments'))
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    # Yes, this is kind of silly
    print _('Using $version.MAILMAN_VERSION ($version.CODENAME)')



if __name__ == '__main__':
    main()
