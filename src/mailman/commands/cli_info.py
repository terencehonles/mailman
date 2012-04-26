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

"""Information about this Mailman instance."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Info'
    ]


import sys

from zope.interface import implementer

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.command import ICLISubCommand
from mailman.rest.helpers import path_to
from mailman.version import MAILMAN_VERSION_FULL



@implementer(ICLISubCommand)
class Info:
    """Information about this Mailman instance."""

    name = 'info'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""
        command_parser.add_argument(
            '-o', '--output',
            action='store', help=_("""\
            File to send the output to.  If not given, standard output is
            used."""))
        command_parser.add_argument(
            '-v', '--verbose',
            action='store_true', help=_("""\
            A more verbose output including the file system paths that Mailman
            is using."""))

    def process(self, args):
        """See `ICLISubCommand`."""
        if args.output is None:
            output = sys.stdout
        else:
            # We don't need to close output because that will happen
            # automatically when the script exits.
            output = open(args.output, 'w')
        print(MAILMAN_VERSION_FULL, file=output)
        print('Python', sys.version, file=output)
        print('config file:', config.filename, file=output)
        print('db url:', config.db.url, file=output)
        print('REST root url:', path_to('/'), file=output)
        print('REST credentials: {0}:{1}'.format(
            config.webservice.admin_user, config.webservice.admin_pass),
            file=output)
        if args.verbose:
            print('File system paths:', file=output)
            longest = 0
            paths = {}
            for attribute in dir(config):
                if attribute.endswith('_DIR') or attribute.endswith('_FILE'):
                    paths[attribute] = getattr(config, attribute)
                longest = max(longest, len(attribute))
            for attribute in sorted(paths):
                print('    {0:{2}} = {1}'.format(
                    attribute, paths[attribute], longest))
