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

"""The 'members' subcommand."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Members',
    ]


import sys
import codecs

from email.utils import formataddr, parseaddr
from operator import attrgetter
from zope.component import getUtility
from zope.interface import implements

from mailman.app.membership import add_member
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.member import AlreadySubscribedError, DeliveryMode



class Members:
    """Manage list memberships.  With no arguments, list all members."""

    implements(ICLISubCommand)

    name = 'members'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        command_parser.add_argument(
            '-a', '--add',
            dest='filename',
            help=_("""\
            Add all member addresses in FILENAME.  FILENAME can be '-' to
            indicate standard input.  Blank lines and lines That start with a
            '#' are ignored."""))
        # Required positional argument.
        command_parser.add_argument(
            'listname', metavar='LISTNAME', nargs=1,
            help=_("""\
            The 'fully qualified list name', i.e. the posting address of the
            mailing list.  It must be a valid email address and the domain
            must be registered with Mailman.  List names are forced to lower
            case."""))

    def process(self, args):
        """See `ICLISubCommand`."""
        assert len(args.listname) == 1, (
            'Unexpected positional arguments: %s' % args.listname)
        fqdn_listname = args.listname[0]
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            self.parser.error(_('No such list: $fqdn_listname'))
        if args.filename is None:
            for address in sorted(mlist.members.addresses,
                                  key=attrgetter('address')):
                print formataddr((address.real_name, address.original_address))
            return
        elif args.filename == '-':
            fp = sys.stdin
        else:
            fp = codecs.open(args.filename, 'r', 'utf-8')
        try:
            for line in fp:
                # Ignore blank lines and lines that start with a '#'.
                if line.startswith('#') or len(line.strip()) == 0:
                    continue
                real_name, email = parseaddr(line)
                # If not given in the input data, parseaddr() will return the
                # empty string, as opposed to the empty unicode.  We need a
                # unicode real name here.
                if real_name == '':
                    real_name = u''
                try:
                    add_member(mlist, email, real_name, None,
                               DeliveryMode.regular,
                               mlist.preferred_language.code)
                except AlreadySubscribedError:
                    # It's okay if the address is already subscribed, just
                    # print a warning and continue.
                    print 'Already subscribed (skipping):', email, real_name
        finally:
            if fp is not sys.stdin:
                fp.close()
        config.db.commit()
