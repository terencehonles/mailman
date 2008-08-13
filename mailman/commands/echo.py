# Copyright (C) 2002-2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""The email command 'echo'."""

__metaclass__ = type
__all__ = [
    'Echo',
    ]


from zope.interface import implements

from mailman.i18n import _
from mailman.interfaces import ContinueProcessing, IEmailCommand


SPACE = ' '



class Echo:
    """The email 'echo' command."""
    implements(IEmailCommand)

    name = 'echo'
    argument_description = '[args]'
    description = _(
        'Echo an acknowledgement.  Arguments are return unchanged.')

    def process(self, mlist, msg, msgdata, arguments, results):
        """See `IEmailCommand`."""
        print >> results, 'echo', SPACE.join(arguments)
        return ContinueProcessing.yes
