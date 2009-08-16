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


from zope.interface import implements

from mailman.i18n import _
from mailman.interfaces.command import ICLISubCommand



class Members:
    """Manage list memberships"""

    implements(ICLISubCommand)

    name = 'members'

    def add(self, parser, command_parser):
        """See `ICLISubCommand`."""

    def process(self, args):
        """See `ICLISubCommand`."""
