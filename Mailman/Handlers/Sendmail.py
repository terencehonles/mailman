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

"""Deliver a message via `sendmail' drop-off.

This module delivers the message via the command line interface to the
sendmail program.  It should work for sendmail clones like Postfix.  It is
expected that sendmail handles final delivery, message queueing, etc.  The
recipient list is only trivially split so that the command line is less than
about 3k in size.

"""

import string
import os
import HandlerAPI
from Mailman import mm_cfg

class SendmailHandlerError(HandlerAPI.HandlerError):
    pass


MAX_CMDLINE = 3000



def process(mlist, msg):
    """Process the message object for the given list.

    The message object is an instance of Mailman.Message and must be fully
    prepared for delivery (i.e. all the appropriate headers must be set).  The
    message object can have the following attributes:

    recips - the list of recipients for the message (required)

    This function processes the message by handing off the delivery of the
    message to a sendmail (or sendmail clone) program.  It can raise a
    SendmailHandlerError if an error status was returned by the sendmail
    program.
    
    """
    if msg.recips == 0:
        # nothing to do!
        return
    # Use -f to set the envelope sender
    cmd = mm_cfg.SENDMAIL_CMD + ' -f ' + msg.GetSender() + ' '
    # make sure the command line is of a manageable size
    recipchunks = []
    currentchunk = []
    chunklen = 0
    for r in msg.recips:
        currentchunk.append(r)
        chunklen = chunklen + len(r) + 1
        if chunklen > MAX_CMDLINE:
            recipchunks.append(string.join(currentchunk))
            currentchunk = []
            chunklen = 0
    # pick up the last one
    if chunklen:
        recipchunks.append(string.join(currentchunk))
    # get all the lines of the message, since we're going to do this over and
    # over again
    msgtext = str(msg)
    # cycle through all chunks
    for recips in recipchunks:
        # TBD: SECURITY ALERT.  This invokes the shell!
        fp = os.popen(cmd + recips, 'w')
        fp.write(msgtext)
        status = fp.close()
        if status:
            errcode = (status & 0xff00) >> 8
            mlist.LogMsg('post', 'post to %s from %s, size=%d, failure=%d' %
                         (mlist.internal_name(), msg.GetSender(),
                          len(msg.body), errcode))
            raise SendmailHandlerError(errcode)
        # Log the successful post
        mlist.LogMsg('post', 'post to %s from %s, size=%d, success' %
                     (mlist.internal_name(), msg.GetSender(), len(msg.body)))
