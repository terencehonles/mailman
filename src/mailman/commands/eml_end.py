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

"""The email commands 'end' and 'stop'."""

__metaclass__ = type
__all__ = [
    'End',
    'Stop',
    ]


from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.command import ContinueProcessing, IEmailCommand



class End:
    """The email 'end' command."""
    implements(IEmailCommand)

    name = 'end'
    argument_description = ''
    description = _('Stop processing commands.')
    short_description = description

    def process(self, mlist, msg, msgdata, arguments, results):
        """See `IEmailCommand`."""
        # Ignore all arguments.
        return ContinueProcessing.no


class Stop(End):
    """The email 'stop' command (an alias for 'end')."""

    name = 'stop'
    description = _("An alias for 'end'.")
    short_description = description
