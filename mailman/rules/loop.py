# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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

"""Look for a posting loop."""

__all__ = ['Loop']
__metaclass__ = type


from zope.interface import implements

from mailman.i18n import _
from mailman.interfaces import IRule



class Loop:
    """Look for a posting loop."""
    implements(IRule)

    name = 'loop'
    description = _("""Look for a posting loop, via the X-BeenThere header.""")
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        # Has this message already been posted to this list?
        been_theres = [value.strip().lower()
                       for value in msg.get_all('x-beenthere', [])]
        return mlist.posting_address in been_theres
