# Copyright (C) 2002-2012 by the Free Software Foundation, Inc.
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

"""Test bounce detection on message files."""


from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'main',
    ]


import sys

from mailman.core.i18n import _
from mailman.options import Options



class ScriptOptions(Options):
    """Options for onebounce."""

    usage = _("""\
%prog [options]

Test the bounce detection for message files.""")

    def add_options(self):
        """See `Options`."""
        self.parser.add_option(
            '-a', '--all',
            default=False, action='store_true',
            help=_("""\
Run the message through all the registered bounce modules.  Normally this
script stops at the first match."""))
        self.parser.add_option(
            '-m', '--module',
            type='string', help=_("""
Run the message through just the named bounce module."""))
        self.parser.add_option(
            '-l', '--list',
            default=False, action='store_true',
            help=_('List all available bounce modules and exit.'))
        self.parser.add_option(
            '-v', '--verbose',
            default=False, action='store_true',
            help=_('Increase verbosity.'))



def main():
    """bin/onebounce"""
    options = ScriptOptions()
    options.initialize()

    if options.options.list:
        print 'list of available bounce modules.'
        sys.exit(0)
