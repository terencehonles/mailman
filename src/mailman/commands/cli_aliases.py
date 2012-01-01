# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""Generate Mailman alias files for your MTA."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Aliases',
    ]


import sys

from operator import attrgetter
from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.mta import (
    IMailTransportAgentAliases, IMailTransportAgentLifecycle)
from mailman.utilities.modules import call_name



class Aliases:
    """Regenerate the aliases appropriate for your MTA."""

    implements(ICLISubCommand)

    name = 'aliases'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        self.parser = parser
        command_parser.add_argument(
            '-o', '--output',
            action='store', help=_("""\
            File to send the output to.  If not given, a file in $VAR/data is
            used.  The argument can be '-' to use standard output.."""))
        command_parser.add_argument(
            '-f', '--format',
            action='store', help=_("""\
            Alternative output format to use.  This is the Python object path
            to an implementation of the `IMailTransportAgentLifecycle`
            interface."""))
        command_parser.add_argument(
            '-s', '--simple',
            action='store_true', default=False, help=_("""\
            Simply output the list of aliases.
            """))

    def process(self, args):
        """See `ICLISubCommand`."""
        if args.format is not None and args.simple:
            self.parser.error(_('Cannot use both -s and -f'))
            # Does not return.
        output = None
        if args.output == '-':
            output = sys.stdout
        elif args.output is None:
            output = None
        else:
            output = args.output
        if args.simple:
            Dummy().regenerate(output)
        else:
            format_arg = (config.mta.incoming
                          if args.format is None
                          else args.format)
            # Call the MTA-specific regeneration method.
            call_name(format_arg).regenerate(output)



class Dummy:
    """Dummy aliases implementation for simpler output format."""

    implements(IMailTransportAgentLifecycle)

    def create(self, mlist):
        """See `IMailTransportAgentLifecycle`."""
        raise NotImplementedError

    def delete(self, mlist):
        """See `IMailTransportAgentLifecycle`."""
        raise NotImplementedError

    def regenerate(self, output=None):
        """See `IMailTransportAgentLifecycle`."""
        fp = None
        close = False
        try:
            if output is None:
                # There's really no place to print the output.
                return
            elif isinstance(output, basestring):
                fp = open(output, 'w')
                close = True
            else:
                fp = output
            self._do_write_file(fp)
        finally:
            if fp is not None and close:
                fp.close()

    def _do_write_file(self, fp):
        # First, sort mailing lists by domain.
        by_domain = {}
        for mlist in getUtility(IListManager).mailing_lists:
            by_domain.setdefault(mlist.mail_host, []).append(mlist)
        sort_key = attrgetter('list_name')
        for domain in sorted(by_domain):
            for mlist in sorted(by_domain[domain], key=sort_key):
                utility = getUtility(IMailTransportAgentAliases)
                for alias in utility.aliases(mlist):
                    print >> fp, alias
                print >> fp
