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

from Mailman import MailList
from Mailman import Utils
from Mailman import mm_cfg
from Mailman.i18n import _

__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=mm_cfg.MAILMAN_VERSION,
                                   usage=_("""\
%prog [options]

List all mailing lists."""))
    parser.add_option('-a', '--advertised',
                      default=False, action='store_true',
                      help=_("""\
List only those mailing lists that are publicly advertised"""))
    parser.add_option('-b', '--bare',
                      default=False, action='store_true',
                      help=_("""\
Displays only the list name, with no description."""))
    parser.add_option('-V', '--virtual-host-overview',
                      default=None, type='string', dest='vhost',
                      help=_("""\
List only those mailing lists that are homed to the given virtual domain.
This only works if the VIRTUAL_HOST_OVERVIEW variable is set."""))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        print >> sys.stderr, _('Unexpected arguments')
        sys.exit(1)
    return parser, opts, args



def main():
    parser, opts, args = parseargs()

    names = Utils.list_names()
    names.sort()
    mlists = []
    longest = 0

    for n in names:
        mlist = MailList.MailList(n, lock=False)
        if opts.advertised and not mlist.advertised:
            continue
        if opts.vhost and mm_cfg.VIRTUAL_HOST_OVERVIEW and \
               opts.vhost.find(mlist.web_page_url) == -1 and \
               mlist.web_page_url.find(opts.vhost) == -1:
            continue
        mlists.append(mlist)
        longest = max(len(mlist.real_name), longest)

    if not mlists and not opts.bare:
        print _('No matching mailing lists found')
        return

    if not opts.bare:
        num_mlists = len(mlists)
        print _('$num_mlists matching mailing lists found:')

    format = '%%%ds - %%.%ds' % (longest, 77 - longest)
    for mlist in mlists:
        if opts.bare:
            print mlist.internal_name()
        else:
            description = mlist.description or _('[no description available]')
            print '   ', format % (mlist.real_name, description)



if __name__ == '__main__':
    main()
