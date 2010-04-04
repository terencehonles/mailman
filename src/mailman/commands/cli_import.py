# Copyright (C) 2010 by the Free Software Foundation, Inc.
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

"""Importing list data into Mailman 3."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Import21',
    ]


from zope.component import getUtility
from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.listmanager import IListManager



class Import21:
    """Import Mailman 2.1 list data."""

    implements(ICLISubCommand)

    name = 'import21'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        self.parser = parser
        # Required positional argument.
        command_parser.add_argument(
            'listname', metavar='LISTNAME', nargs=1,
            help=_("""\
            The 'fully qualified list name', i.e. the posting address of the
            mailing list to inject the message into."""))

    def process(self, args):
        """See `ICLISubCommand`."""
        # Could be None or sequence of length 0.
        if args.listname is None:
            self.parser.error(_('List name is required'))
            return
        assert len(args.listname) == 1, (
            'Unexpected positional arguments: %s' % args.listname)
        fqdn_listname = args.listname[0]
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            self.parser.error(_('No such list: $fqdn_listname'))
            return
        
