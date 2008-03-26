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

from mailman import Defaults
from mailman import Version
from mailman.configuration import config
from mailman.i18n import _
from mailman.options import Options



class ScriptOptions(Options):
    usage=_("""\
%prog [options]

List all mailing lists.""")

    def add_options(self):
        super(ScriptOptions, self).add_options()
        self.parser.add_option(
            '-a', '--advertised',
            default=False, action='store_true',
            help=_("""\
List only those mailing lists that are publicly advertised"""))
        self.parser.add_option(
            '-b', '--bare',
            default=False, action='store_true',
            help=_("""\
Displays only the list name, with no description."""))
        self.parser.add_option(
            '-d', '--domain',
            default=[], type='string', action='append',
            dest='domains', help=_("""\
List only those mailing lists that match the given virtual domain, which may
be either the email host or the url host name.  Multiple -d options may be
given."""))
        self.parser.add_option(
            '-f', '--full',
            default=False, action='store_true',
            help=_("""\
Print the full list name, including the posting address."""))

    def sanity_check(self):
        if len(self.arguments) > 0:
            self.parser.error(_('Unexpected arguments'))



def main():
    options = ScriptOptions()
    options.initialize()

    mlists = []
    longest = 0

    listmgr = config.db.list_manager
    for fqdn_name in sorted(listmgr.names):
        mlist = listmgr.get(fqdn_name)
        if options.options.advertised and not mlist.advertised:
            continue
        if options.options.domains:
            for domain in options.options.domains:
                if domain in mlist.web_page_url or domain == mlist.host_name:
                    mlists.append(mlist)
                    break
        else:
            mlists.append(mlist)
        if options.options.full:
            name = mlist.fqdn_listname
        else:
            name = mlist.real_name
        longest = max(len(name), longest)

    if not mlists and not options.options.bare:
        print _('No matching mailing lists found')
        return

    if not options.options.bare:
        num_mlists = len(mlists)
        print _('$num_mlists matching mailing lists found:')

    format = '%%%ds - %%.%ds' % (longest, 77 - longest)
    for mlist in mlists:
        if options.options.full:
            name = mlist.fqdn_listname
        else:
            name = mlist.real_name
        if options.options.bare:
            print name
        else:
            description = mlist.description or _('[no description available]')
            print '   ', format % (name, description)
