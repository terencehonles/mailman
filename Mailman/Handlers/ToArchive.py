# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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

"""Add the message to the archives."""

import time

from Mailman import mm_cfg
from Mailman.Queue.sbcache import get_switchboard
from Mailman.pythonlib.StringIO import StringIO



def process(mlist, msg, msgdata):
    # short circuits
    if msgdata.get('isdigest') or not mlist.archive:
        return
    # Common practice seems to favor "X-No-Archive: yes".  I'm keeping
    # "X-Archive: no" for backwards compatibility.
    if msg.get('x-no-archive', '').lower() == 'yes' or \
           msg.get('x-archive', '').lower() == 'no':
        return
    # Send the message to the archiver queue
    archq = get_switchboard(mm_cfg.ARCHQUEUE_DIR)
    # Send the message to the queue
    msgdata.setdefault('received_time', time.time())
    archq.enqueue(msg, msgdata)
