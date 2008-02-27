# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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

import os
import sys
import optparse

from mailman import MailList
from mailman import Version
from mailman.i18n import _
from mailman.initialize import initialize

# Work around known problems with some RedHat cron daemons
import signal
signal.signal(signal.SIGCHLD, signal.SIG_DFL)



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

Dispatch digests for lists w/pending messages and digest_send_periodic
set."""))
    parser.add_option('-l', '--listname',
                      type='string', default=[], action='append',
                      dest='listnames', help=_("""\
Send the digest for the given list only, otherwise the digests for all
lists are sent out.  Multiple -l options may be given."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    return opts, args, parser



def main():
    opts, args, parser = parseargs()
    initialize(opts.config)

    for listname in set(opts.listnames or config.list_manager.names):
        mlist = MailList.MailList(listname, lock=False)
        if mlist.digest_send_periodic:
            mlist.Lock()
            try:
                try:
                    mlist.send_digest_now()
                    mlist.Save()
                # We are unable to predict what exception may occur in digest
                # processing and we don't want to lose the other digests, so
                # we catch everything.
                except Exception, errmsg:
                    print >> sys.stderr, \
                      'List: %s: problem processing %s:\n%s' % \
                        (listname,
                         os.path.join(mlist.full_path(), 'digest.mbox'),
                         errmsg)
            finally:
                mlist.Unlock()



if __name__ == '__main__':
    main()
