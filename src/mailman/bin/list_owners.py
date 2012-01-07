# Copyright (C) 2002-2012 by the Free Software Foundation, Inc.
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

from zope.component import getUtility

from mailman.MailList import MailList
from mailman.core.i18n import _
from mailman.initialize import initialize
from mailman.interfaces.listmanager import IListManager
from mailman.version import MAILMAN_VERSION



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
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

    list_manager = getUtility(IListManager)
    listnames = set(args or list_manager.names)
    bylist = {}

    for listname in listnames:
        mlist = list_manager.get(listname)
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
