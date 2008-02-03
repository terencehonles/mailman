# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Check if any previous rules have matched."""

__all__ = ['Any']
__metaclass__ = type


from zope.interface import implements

from Mailman.i18n import _
from Mailman.interfaces import IRule



class Any:
    """Look for any previous rule match."""
    implements(IRule)

    name = 'any'
    description = _('Look for any previous rule hit.')
    record = False

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        return len(msgdata.get('rules', [])) > 0
