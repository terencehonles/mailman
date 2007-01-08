# Copyright (C) 1998-2007 by the Free Software Foundation, Inc.
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

from Mailman import Defaults
from Mailman import MailList
from Mailman import Utils
from Mailman import Version
from Mailman.i18n import _
from Mailman.initialize import initialize

__i18n_templates__ = True



def parseargs():
    parser = optparse.OptionParser(version=Version.MAILMAN_VERSION,
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
    parser.add_option('-d', '--domain',
                      default=[], type='string', action='append',
                      dest='domains', help=_("""\
List only those mailing lists that match the given virtual domain, which may
be either the email host or the url host name.  Multiple -d options may be
given."""))
    parser.add_option('-f', '--full',
                      default=False, action='store_true',
                      help=_("""\
Print the full list name, including the posting address."""))
    parser.add_option('-C', '--config',
                      help=_('Alternative configuration file to use'))
    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        parser.error(_('Unexpected arguments'))
    return parser, opts, args



def main():
    parser, opts, args = parseargs()
    initialize(opts.config)

    names = list(Utils.list_names())
    names.sort()
    mlists = []
    longest = 0

    for n in names:
        mlist = MailList.MailList(n, lock=False)
        if opts.advertised and not mlist.advertised:
            continue
        if opts.domains:
            for domain in opts.domains:
                if domain in mlist.web_page_url or domain == mlist.host_name:
                    mlists.append(mlist)
                    break
        else:
            mlists.append(mlist)
        if opts.full:
            name = mlist.fqdn_listname
        else:
            name = mlist.real_name
        longest = max(len(name), longest)

    if not mlists and not opts.bare:
        print _('No matching mailing lists found')
        return

    if not opts.bare:
        num_mlists = len(mlists)
        print _('$num_mlists matching mailing lists found:')

    format = '%%%ds - %%.%ds' % (longest, 77 - longest)
    for mlist in mlists:
        if opts.full:
            name = mlist.fqdn_listname
        else:
            name = mlist.real_name
        if opts.bare:
            print name
        else:
            description = mlist.description or _('[no description available]')
            print '   ', format % (name, description)
