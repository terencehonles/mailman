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

import os
import time
import socket
import sha
import marshal

from Mailman import mm_cfg
from Mailman import Utils
from Mailman.Handlers import HandlerAPI
from Mailman.pythonlib import smtplib



def process(mlist, msg):
    if msg.recips == 0:
        # nothing to do!
        return
    # I want to record how long the SMTP dialog takes because this will help
    # diagnose whether we need to rewrite this module to relinquish the list
    # lock or not.
    t0 = time.time()
    refused = {}
    try:
        conn = smtplib.SMTP(mm_cfg.SMTPHOST, mm_cfg.SMTPPORT)
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
        mlist.LogMsg('smtp', 'All recipients refused: %s' % e)
        # no recipients ever received the message
        queue_message(mlist, msg)
    #
    # Go through all refused recipients and deal with them if possible
    tempfailures = []
    for recip, (code, smtpmsg) in refused.items():
        # DRUMS is an internet draft, but it says:
        #
        #    [RFC-821] incorrectly listed the error where an SMTP server
        #    exhausts its implementation limit on the number of RCPT commands
        #    ("too many recipients") as having reply code 552.  The correct
        #    reply code for this condition is 452. Clients SHOULD treat a 552
        #    code in this case as a temporary, rather than permanent failure
        #    so the logic below works.
        #
        if code >= 500 and code <> 552:
            # It's a permanent failure for this recipient so register it.  We
            # don't save the list between each registration because we assume
            # it happens around the whole message delivery sequence
            mlist.RegisterBounce(recip, msg, saveifdirty=0)
        else:
            # deal with persistent transient failures by queuing them up for
            # future delivery.
            mlist.LogMsg('smtp-failure', '%d %s (%s)' % (code, recip, smtpmsg))
            tempfailures.append(recip)
    if tempfailures:
        queue_message(mlist, msg, tempfailures)



def queue_message(mlist, msg, recips=None):
    if recips is None:
        # i.e. total delivery failure
        recips = msg.recips
    # calculate a unique name for this file
    text = str(msg)
    filebase = sha.new(text).hexdigest()
    msgfile = os.path.join(mm_cfg.QUEUE_DIR, filebase + '.msg')
    dbfile = os.path.join(mm_cfg.QUEUE_DIR, filebase + '.db')
    # Initialize the information about this message delivery.  It's possible a
    # delivery attempt has been previously tried on this message, in which
    # case, we'll just update the data.  We should probably do /some/ timing
    # out of failed deliveries.
    try:
        dbfp = open(dbfile)
        msgdata = marshal.load(dbfp)
        dbfp.close()
        msgdata['last_recip_count'] = len(msgdata['recips'])
        msgdata['recips'] = recips
        msgdata['attempts'] = msgdata['attempts'] + 1
        existsp = 1
    except (EOFError, ValueError, TypeError, IOError):
        msgdata = {'listname'        : mlist.internal_name(),
                   'recips'          : recips,
                   'attempts'        : 1,
                   'last_recip_count': -1,
                   # any other stats we need?
                   }
        existsp = 0
    # write the data file
    dbfp = Utils.open_ex(dbfile, 'w')
    marshal.dump(msgdata, dbfp)
    dbfp.close()
    # if it doesn't already exist, write the message file
    if not existsp:
        msgfp = Utils.open_ex(msgfile, 'w')
        msgfp.write(text)
        msgfp.close()
    # this is a signal to qrunner
    msg.failedcount = len(recips)
