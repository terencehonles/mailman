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

import sys
import optparse

from mailman import errors
from mailman import MailList
from mailman.configuration import config
from mailman.core.i18n import _
from mailman.version import MAILMAN_VERSION

# Work around known problems with some RedHat cron daemons
import signal
signal.signal(signal.SIGCHLD, signal.SIG_DFL)



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
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

    listnames = set(args or config.list_manager.names)
    if not listnames:
        print _('Nothing to do.')
        sys.exit(0)

    for listname in listnames:
        try:
            # Be sure the list is locked
            mlist = MailList.MailList(listname)
        except errors.MMListError:
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
