#! @PYTHON@
#
# Copyright (C) 2001-2008 by the Free Software Foundation, Inc.
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

from mailman import MailList
from mailman.configuration import config
from mailman.i18n import _
from mailman.initialize import initialize
from mailman.version import MAILMAN_VERSION



def parseargs():
    parser = optparse.OptionParser(version=MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

Regenerate the Mailman specific MTA aliases from scratch.  The actual output
depends on the value of the 'MTA' variable in your etc/mailman.cfg file."""))
    parser.add_option('-q', '--quiet',
                      default=False, action='store_true', help=_("""\
Some MTA output can include more verbose help text.  Use this to tone down the
verbosity."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if args:
        parser.print_error(_('Unexpected arguments'))
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)

    # Import the MTA specific module
    modulename = 'mailman.MTA.' + config.MTA
    __import__(modulename)
    MTA = sys.modules[modulename]

    # We need to acquire a lock so nobody tries to update the files while
    # we're doing it.
    lock = MTA.makelock()
    lock.lock()
    # Group lists by virtual hostname
    mlists = {}
    for listname in config.list_manager.names:
        mlist = MailList.MailList(listname, lock=False)
        mlists.setdefault(mlist.host_name, []).append(mlist)
    try:
        MTA.clear()
        if not mlists:
            MTA.create(None, nolock=True, quiet=opts.quiet)
        else:
            for hostname, vlists in mlists.items():
                for mlist in vlists:
                    MTA.create(mlist, nolock=True, quiet=opts.quiet)
                    # Be verbose for only the first printed list
                    quiet = True
    finally:
        lock.unlock(unconditionally=True)



if __name__ == '__main__':
    main()
