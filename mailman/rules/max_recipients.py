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

"""The maximum number of recipients rule."""

__all__ = ['MaximumRecipients']
__metaclass__ = type


from email.utils import getaddresses
from zope.interface import implements

from mailman.i18n import _
from mailman.interfaces import IRule



class MaximumRecipients:
    """The maximum number of recipients rule."""
    implements(IRule)

    name = 'max-recipients'
    description = _('Catch messages with too many explicit recipients.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        # Zero means any number of recipients are allowed.
        if mlist.max_num_recipients == 0:
            return False
        # Figure out how many recipients there are
        recipients = getaddresses(msg.get_all('to', []) +
                                  msg.get_all('cc', []))
        return len(recipients) >= mlist.max_num_recipients
