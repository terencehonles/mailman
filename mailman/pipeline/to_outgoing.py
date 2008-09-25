# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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

"""Re-queue the message to the outgoing queue.

This module is only for use by the IncomingRunner for delivering messages
posted to the list membership.  Anything else that needs to go out to some
recipient should just be placed in the out queue directly.
"""

__metaclass__ = type
__all__ = ['ToOutgoing']


from zope.interface import implements

from mailman.configuration import config
from mailman.i18n import _
from mailman.interfaces import IHandler, Personalization
from mailman.queue import Switchboard



class ToOutgoing:
    """Send the message to the outgoing queue."""

    implements(IHandler)

    name = 'to-outgoing'
    description = _('Send the message to the outgoing queue.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        interval = config.VERP_DELIVERY_INTERVAL
        # Should we VERP this message?  If personalization is enabled for this
        # list and VERP_PERSONALIZED_DELIVERIES is true, then yes we VERP it.
        # Also, if personalization is /not/ enabled, but
        # VERP_DELIVERY_INTERVAL is set (and we've hit this interval), then
        # again, this message should be VERPed. Otherwise, no.
        #
        # Note that the verp flag may already be set, e.g. by mailpasswds
        # using VERP_PASSWORD_REMINDERS.  Preserve any existing verp flag.
        if 'verp' in  msgdata:
            pass
        elif mlist.personalize <> Personalization.none:
            if config.VERP_PERSONALIZED_DELIVERIES:
                msgdata['verp'] = True
        elif interval == 0:
            # Never VERP
            pass
        elif interval == 1:
            # VERP every time
            msgdata['verp'] = True
        else:
            # VERP every `interval' number of times
            msgdata['verp'] = not (int(mlist.post_id) % interval)
        # And now drop the message in qfiles/out
        outq = Switchboard(config.OUTQUEUE_DIR)
        outq.enqueue(msg, msgdata, listname=mlist.fqdn_listname)
