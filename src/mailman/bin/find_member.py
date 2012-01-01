# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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
import optparse

from mailman import errors
from mailman import MailList
from mailman.configuration import config
from mailman.core.i18n import _
from mailman.version import MAILMAN_VERSION


AS_MEMBER   = 0x01
AS_OWNER    = 0x02



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] regex [regex ...]

Find all lists that a member's address is on.

The interaction between -l and -x (see below) is as follows.  If any -l option
is given then only the named list will be included in the search.  If any -x
option is given but no -l option is given, then all lists will be search
except those specifically excluded.

Regular expression syntax uses the Python 're' module.  Complete
specifications are at:

http://www.python.org/doc/current/lib/module-re.html

Address matches are case-insensitive, but case-preserved addresses are
displayed."""))
    parser.add_option('-l', '--listname',
                      type='string', default=[], action='append',
                      dest='listnames',
                      help=_('Include only the named list in the search'))
    parser.add_option('-x', '--exclude',
                      type='string', default=[], action='append',
                      dest='excludes',
                      help=_('Exclude the named list from the search'))
    parser.add_option('-w', '--owners',
                      default=False, action='store_true',
                      help=_('Search list owners as well as members'))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if not args:
        parser.print_help()
        print >> sys.stderr, _('Search regular expression required')
        sys.exit(1)
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    config.load(opts.config)

    listnames = opts.listnames or config.list_manager.names
    includes = set(listname.lower() for listname in listnames)
    excludes = set(listname.lower() for listname in opts.excludes)
    listnames = includes - excludes

    if not listnames:
        print _('No lists to search')
        return

    cres = []
    for r in args:
        cres.append(re.compile(r, re.IGNORECASE))
    # dictionary of {address, (listname, ownerp)}
    matches = {}
    for listname in listnames:
        try:
            mlist = MailList.MailList(listname, lock=False)
        except errors.MMListError:
            print _('No such list: $listname')
            continue
        if opts.owners:
            owners = mlist.owner
        else:
            owners = []
        for cre in cres:
            for member in mlist.getMembers():
                if cre.search(member):
                    addr = mlist.getMemberCPAddress(member)
                    entries = matches.get(addr, {})
                    aswhat = entries.get(listname, 0)
                    aswhat |=  AS_MEMBER
                    entries[listname] = aswhat
                    matches[addr] = entries
            for owner in owners:
                if cre.search(owner):
                    entries = matches.get(owner, {})
                    aswhat = entries.get(listname, 0)
                    aswhat |= AS_OWNER
                    entries[listname] = aswhat
                    matches[owner] = entries
    addrs = matches.keys()
    addrs.sort()
    for k in addrs:
        hits = matches[k]
        lists = hits.keys()
        print k, _('found in:')
        for name in lists:
            aswhat = hits[name]
            if aswhat & AS_MEMBER:
                print '    ', name
            if aswhat & AS_OWNER:
                print '    ', name, _('(as owner)')



if __name__ == '__main__':
    main()
