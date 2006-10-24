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

import sys
import optparse

from Mailman import Errors
from Mailman import MailList
from Mailman import Utils
from Mailman import Version
from Mailman.configuration import config
from Mailman.i18n import _

# Work around known problems with some RedHat cron daemons
import signal
signal.signal(signal.SIGCHLD, signal.SIG_DFL)

__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options] [listname ...]

Increment the digest volume number and reset the digest number to one.  All
the lists named on the command line are bumped.  If no list names are given,
all lists are bumped."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    return opts, args, parser



def main():
    opts, args, parser = parseargs()
    config.load(opts.config)

    listnames = set(args or Utils.list_names())
    if not listnames:
        print _('Nothing to do.')
        sys.exit(0)

    for listname in listnames:
        try:
            # Be sure the list is locked
            mlist = MailList.MailList(listname)
        except Errors.MMListError, e:
            parser.print_help()
            print >> sys.stderr, _('No such list: $listname')
            sys.exit(1)
        try:
            mlist.bump_digest_volume()
        finally:
            mlist.Save()
            mlist.Unlock()



if __name__ == '__main__':
    main()
