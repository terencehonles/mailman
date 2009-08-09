# Copyright (C) 2009 by the Free Software Foundation, Inc.
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

"""The 'lists' subcommand."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Lists',
    ]


from zope.interface import implements

from mailman.config import config
from mailman.i18n import _
from mailman.interfaces.command import ICLISubCommand



class Lists:
    """The `lists` subcommand."""

    implements(ICLISubCommand)

    def add(self, subparser):
        """See `ICLISubCommand`."""
        lists_parser = subparser.add_parser(
            'lists', help=_('List all mailing lists'))
        lists_parser.add_argument(
            '-a', '--advertised',
            default=False, action='store_true',
            help=_(
                'List only those mailing lists that are publicly advertised'))
        lists_parser.add_argument(
            '-b', '--bare',
            default=False, action='store_true',
            help=_('Show only the list name, with no description'))
        lists_parser.add_argument(
            '-d', '--domain',
            action='append', help=_("""\
            List only those mailing lists hosted on the given domain, which
            must be the email host name.  Multiple -d options may be given.
            """))
        lists_parser.add_argument(
            '-f', '--full',
            default=False, action='store_true',
            help=_(
                'Show the full mailing list name (i.e. the posting address'))
        lists_parser.set_defaults(func=self.process)

    def process(self, args):
        """See `ICLISubCommand`."""
        mailing_lists = []
        list_manager = config.db.list_manager
        # Gather the matching mailing lists.
        for fqdn_name in sorted(list_manager.names):
            mlist = list_manager.get(fqdn_name)
            if args.advertised and not mlist.advertised:
                continue
            if args.domains and mlist.host_name not in args.domains:
                continue
            mailing_lists.append(mlist)
        # Maybe no mailing lists matched.
        if len(mailing_lists) == 0:
            if not args.bare:
                print _('No matching mailing lists found')
            return
        if not args.bare:
            count = len(mailing_lists)
            print _('$count matching mailing lists found:')
        # Calculate the longest mailing list name.
        longest = len(
            max(mlist.fqdn_listname for mlist in mailing_lists)
            if args.full else
            max(mlist.real_name for mlist in mailing_lists))
        # Print it out.
        for mlist in mailing_lists:
            name = (mlist.fqdn_listname if args.full else mlist.real_name)
            if args.bare:
                print name
            else:
                description = (mlist.description
                               if mlist.description is not None
                               else _('[no description available]'))
                print '{0:{2}} - {1:{3}}'.format(
                    name, description, longest, 77 - longest)
