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

"""The maximum message size rule."""

__all__ = ['MaximumSize']
__metaclass__ = type


from zope.interface import implements

from Mailman.i18n import _
from Mailman.interfaces import IRule



class MaximumSize:
    """The implicit destination rule."""
    implements(IRule)

    name = 'max-size'
    description = _('Catch messages that are bigger than a specified maximum.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        if mlist.max_message_size == 0:
            return False
        assert hasattr(msg, 'original_size'), (
            'Message was not sized on initial parsing.')
        # The maximum size is specified in 1024 bytes.
        return msg.original_size / 1024.0 > mlist.max_message_size
