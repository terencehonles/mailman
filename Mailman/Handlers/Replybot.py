# Copyright (C) 1998 by the Free Software Foundation, Inc.
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

"""Handler for auto-responses.
"""

import string
import time
import HandlerAPI

from Mailman import Utils
from Mailman import Message



def process(mlist, msg):
    # "X-Ack: No" header in the original message disables the replybot
    ack = string.lower(msg.get('x-ack', ''))
    if ack == 'no':
        return
    # Check to see if the list is even configured to autorespond to this email
    # message.  Note: the mailowner script sets the `toadmin' attribute, and
    # the mailcmd script sets the `torequest' attribute.
    toadmin = getattr(msg, 'toadmin', 0)
    torequest = getattr(msg, 'torequest', 0)
    if (toadmin and not mlist.autorespond_admin) or \
       (torequest and not mlist.autorespond_requests) or \
       (not toadmin and not torequest and not mlist.autorespond_postings):
        return
    #
    # Now see if we're in the grace period for this sender (guaranteed to be
    # lower cased).  graceperiod <= 0 means always autorespond, as does an
    # "X-Ack: yes" header (useful for debugging).
    sender = msg.GetSender()
    now = time.time()
    graceperiod = mlist.autoresponse_graceperiod
    if graceperiod > 0 and ack <> 'yes':
        if toadmin:
            quite_until = mlist.admin_responses.get(sender, 0)
        elif torequest:
            quite_until = mlist.request_responses.get(sender, 0)
        else:
            quite_until = mlist.postings_responses.get(sender, 0)
        if quite_until > now:
            return
    #
    # Okay, we know we're going to auto-respond to this sender, craft the
    # message, send it, and update the database.
    subject = 'Auto-response for your message to ' + \
              msg.get('to',  'the "%s" mailing list' % mlist.real_name)
    # Do string interpolation
    d = Utils.SafeDict({'listname'    : mlist.real_name,
                        'listurl'     : mlist.GetScriptURL('listinfo'),
                        'requestemail': mlist.GetRequestEmail(),
                        'adminemail'  : mlist.GetAdminEmail(),
                        })
    if toadmin:
        text = mlist.autoresponse_admin_text % d
    elif torequest:
        text = mlist.autoresponse_request_text % d
    else:
        text = mlist.autoresponse_postings_text % d
    outmsg = Message.UserNotification(sender, mlist.GetAdminEmail(),
                                      subject, text)
    outmsg['X-Mailer'] = 'The Mailman Replybot '
    # prevent recursions and mail loops!
    outmsg['X-Ack'] = 'No'
    HandlerAPI.DeliverToUser(mlist, outmsg)
    # update the grace period database
    if graceperiod > 0:
        # graceperiod is in days, we need # of seconds
        quite_until = now + graceperiod * 24 * 60 * 60
        if toadmin:
            mlist.admin_responses[sender] = quite_until
        elif torequest:
            mlist.request_responses[sender] = quite_until
        else:
            mlist.postings_responses[sender] = quite_until
