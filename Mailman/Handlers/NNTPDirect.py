# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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

"""Send messages to the NNTP server."""

import os
import time
import re
import socket
import nntplib

from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog
from Mailman.pythonlib.StringIO import StringIO

COMMA = ','



def process(mlist, msg, msgdata):
    # Flatten the message object, stick it in a StringIO object and post that
    # resulting thing to the newsgroup.
    fp = StringIO(str(msg))
    conn = None
    try:
        try:
            conn = nntplib.NNTP(mlist.nntp_host, readermode=1,
                                user=mm_cfg.NNTP_USERNAME,
                                password=mm_cfg.NNTP_PASSWORD)
            conn.post(fp)
        except nntplib.error_temp, e:
            syslog('error', '(NNTPDirect) NNTP error for list "%s": %s' %
                   (mlist.internal_name(), e))
        except socket.error, e:
            syslog('error', '(NNTPDirect) socket error for list "%s": %s'
                   % (mlist.internal_name(), e))
    finally:
        if conn:
            conn.quit()
