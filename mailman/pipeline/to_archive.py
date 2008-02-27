# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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

"""Add the message to the archives."""

__metaclass__ = type
__all__ = ['ToArchive']


from zope.interface import implements

from mailman.configuration import config
from mailman.i18n import _
from mailman.interfaces import IHandler
from mailman.queue import Switchboard



class ToArchive:
    """Add the message to the archives."""

    implements(IHandler)

    name = 'to-archive'
    description = _('Add the message to the archives.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        # Short circuits.
        if msgdata.get('isdigest') or not mlist.archive:
            return
        # Common practice seems to favor "X-No-Archive: yes".  No other value
        # for this header seems to make sense, so we'll just test for it's
        # presence.  I'm keeping "X-Archive: no" for backwards compatibility.
        if 'x-no-archive' in msg or msg.get('x-archive', '').lower() == 'no':
            return
        # Send the message to the archiver queue
        archq = Switchboard(config.ARCHQUEUE_DIR)
        # Send the message to the queue
        archq.enqueue(msg, msgdata)
