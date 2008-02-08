# Copyright (C) 2002-2008 by the Free Software Foundation, Inc.
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

from Mailman import Version
from Mailman.MailList import MailList
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.initialize import initialize


__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] [listname ...]

List the owners of a mailing list, or all mailing lists if no list names are
given."""))
    parser.add_option('-w', '--with-listnames',
                      default=False, action='store_true',
                      help=_("""\
Group the owners by list names and include the list names in the output.
Otherwise, the owners will be sorted and uniquified based on the email
address."""))
    parser.add_option('-m', '--moderators',
                      default=False, action='store_true',
                      help=_('Include the list moderators in the output.'))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)

    listmgr = config.db.list_manager
    listnames = set(args or listmgr.names)
    bylist = {}

    for listname in listnames:
        mlist = listmgr.get(listname)
        addrs = [addr.address for addr in mlist.owners.addresses]
        if opts.moderators:
            addrs.extend([addr.address for addr in mlist.moderators.addresses])
        bylist[listname] = addrs

    if opts.with_listnames:
        for listname in listnames:
            unique = set()
            for addr in bylist[listname]:
                unique.add(addr)
            keys = list(unique)
            keys.sort()
            print listname
            for k in keys:
                print '\t', k
    else:
        unique = set()
        for listname in listnames:
            for addr in bylist[listname]:
                unique.add(addr)
        for k in sorted(unique):
            print k



if __name__ == '__main__':
    main()
