# Copyright (C) 1998,1999,2000,2001,2002 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Re-queue the message to the outgoing queue.

This module is only for use by the IncomingRunner for delivering messages
posted to the list membership.  Anything else that needs to go out to some
recipient should just be placed in the out queue directly.
"""

from Mailman import mm_cfg
from Mailman.Queue.sbcache import get_switchboard



def process(mlist, msg, msgdata):
    # Do VERP calculation for non-personalized interval delivery.  BAW: We
    # can't do this in OutgoingRunner.py (where it was originally) because
    # that runner loads the list unlocked and we can't have it re-load the
    # list state for every cycle through its mainloop.
    interval = mm_cfg.VERP_DELIVERY_INTERVAL
    # If occasional VERPing is turned on, and we haven't't already made a
    # VERPing decision...
    if interval > 0 and not msgdata.has_key('verp'):
        if interval == 1:
            # VERP every time
            msgdata['verp'] = 1
        msgdata['verp'] = not int(mlist.post_id) % interval
    # And now drop the message in qfiles/out
    outq = get_switchboard(mm_cfg.OUTQUEUE_DIR)
    outq.enqueue(msg, msgdata, listname=mlist.internal_name())
