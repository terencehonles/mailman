# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""A rule which always matches."""

__metaclass__ = type
__all__ = ['Truth']


from zope.interface import implements

from mailman.i18n import _
from mailman.interfaces import IRule



class Truth:
    """Look for any previous rule match."""
    implements(IRule)

    name = 'truth'
    description = _('A rule which always matches.')
    record = False

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        return True
