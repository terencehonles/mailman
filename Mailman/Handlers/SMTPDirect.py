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

"""Local SMTP direct drop-off.

This module delivers messages via SMTP to a locally specified daemon.  This
should be compatible with any modern SMTP server.  It is expected that the MTA
handles all final delivery.  We have to play tricks so that the list object
isn't locked while delivery occurs synchronously.

"""

import time
import socket
from Mailman import mm_cfg
from Mailman.pythonlib import smtplib



def process(mlist, msg):
    if msg.recips == 0:
        # nothing to do!
        return
    # I want to record how long the SMTP dialog takes because this will help
    # diagnose whether we need to rewrite this module to relinquish the list
    # lock or not.
    t0 = time.time()
    conn = smtplib.SMTP(mm_cfg.SMTPHOST, mm_cfg.SMTPPORT)
    refused = {}
    try:
        try:
            # make sure the connect happens, which won't be done by the
            # constructor if SMTPHOST is false
            envsender = mlist.GetAdminEmail()
            refused = conn.sendmail(envsender, msg.recips, str(msg))
        finally:
            t1 = time.time()
            mlist.LogMsg('smtp',
                         'smtp for %d recips, completed in %.3f seconds' %
                         (len(msg.recips), (t1-t0)))
            conn.quit()
    except smtplib.SMTPRecipientsRefused, e:
        refused = e.recipients
    # MTA not responding, or other socket problems, or any other kind of
    # SMTPException.  In that case, nothing got delivered
    except (socket.error, smtplib.SMTPException), e:
        mlist.LogMsg('smtp', 'Some other exception occurred:\n' + `e`)
        mlist.LogMsg('smtp', 'All recipients refused')
    #
    # Go through all refused recipients and deal with them if possible
    for recip, (code, smtpmsg) in refused.items():
        if code >= 500:
            # It's a permanent failure for this recipient so register it.  We
            # don't save the list between each registration because we assume
            # it happens around the whole message delivery sequence
            mlist.RegisterBounce(recip, msg, saveifdirty=0)
        # TBD: should we do anything with persistent transient failures, like
        # queue them up and try to resend them?  Should we log the smtp error
        # messages, or do any other processing of failures?  Lots of
        # questions...
        else:
            mlist.LogMsg('smtp-failure', '%d %s (%s)' % (code, recip, smtpmsg))
