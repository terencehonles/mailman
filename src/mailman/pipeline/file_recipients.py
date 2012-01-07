# Copyright (C) 2001-2012 by the Free Software Foundation, Inc.
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

"""Get the normal delivery recipients from a Sendmail style :include: file."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'FileRecipients',
    ]


import os
import errno

from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler



class FileRecipients:
    """Get the normal delivery recipients from an include file."""

    implements(IHandler)

    name = 'file-recipients'
    description = _('Get the normal delivery recipients from an include file.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        if 'recipients' in msgdata:
            return
        filename = os.path.join(mlist.data_path, 'members.txt')
        try:
            with open(filename) as fp:
                addrs = set(line.strip() for line in fp)
        except IOError as error:
            if error.errno != errno.ENOENT:
                raise
            msgdata['recipients'] = set()
            return
        # If the sender is a member of the list, remove them from the file
        # recipients.
        member = mlist.members.get_member(msg.sender)
        if member is not None:
            addrs.discard(member.address.email)
        msgdata['recipients'] = addrs
