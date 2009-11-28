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

"""Generate Mailman alias files for your MTA."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Aliases',
    ]


import sys

from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand
from mailman.utilities.modules import call_name



class Aliases:
    """Regenerate the aliases appropriate for your MTA."""

    implements(ICLISubCommand)

    name = 'aliases'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        command_parser.add_argument(
            '-o', '--output',
            action='store', help=_("""\
            File to send the output to.  If not given, a file in $VAR/data is
            used.  The argument can be '-' to use standard output.."""))

    def process(self, args):
        """See `ICLISubCommand`."""
        output = None
        if args.output == '-':
            output = sys.stdout
        elif args.output is None:
            output = None
        else:
            output = args.output
        # Call the MTA-specific regeneration method.
        call_name(config.mta.incoming).regenerate(output)
