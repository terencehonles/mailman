# Copyright (C) 1998-2009 by the Free Software Foundation, Inc.
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

"""Handler for auto-responses."""

__metaclass__ = type
__all__ = ['Replybot']


import time
import logging
import datetime

from string import Template
from zope.interface import implements

from mailman import Message
from mailman import Utils
from mailman.i18n import _
from mailman.interfaces import IHandler


log = logging.getLogger('mailman.error')
NODELTA = datetime.timedelta()



def process(mlist, msg, msgdata):
    # Normally, the replybot should get a shot at this message, but there are
    # some important short-circuits, mostly to suppress 'bot storms, at least
    # for well behaved email bots (there are other governors for misbehaving
    # 'bots).  First, if the original message has an "X-Ack: No" header, we
    # skip the replybot.  Then, if the message has a Precedence header with
    # values bulk, junk, or list, and there's no explicit "X-Ack: yes" header,
    # we short-circuit.  Finally, if the message metadata has a true 'noack'
    # key, then we skip the replybot too.
    ack = msg.get('x-ack', '').lower()
    if ack == 'no' or msgdata.get('noack'):
        return
    precedence = msg.get('precedence', '').lower()
    if ack <> 'yes' and precedence in ('bulk', 'junk', 'list'):
        return
    # Check to see if the list is even configured to autorespond to this email
    # message.  Note: the mailowner script sets the `toadmin' or `toowner' key
    # (which for replybot purposes are equivalent), and the mailcmd script
    # sets the `torequest' key.
    toadmin = msgdata.get('toowner')
    torequest = msgdata.get('torequest')
    if ((toadmin and not mlist.autorespond_admin) or
           (torequest and not mlist.autorespond_requests) or \
           (not toadmin and not torequest and not mlist.autorespond_postings)):
        return
    # Now see if we're in the grace period for this sender.  graceperiod <= 0
    # means always autorespond, as does an "X-Ack: yes" header (useful for
    # debugging).
    sender = msg.get_sender()
    now = time.time()
    graceperiod = mlist.autoresponse_graceperiod
    if graceperiod > NODELTA and ack <> 'yes':
        if toadmin:
            quiet_until = mlist.admin_responses.get(sender, 0)
        elif torequest:
            quiet_until = mlist.request_responses.get(sender, 0)
        else:
            quiet_until = mlist.postings_responses.get(sender, 0)
        if quiet_until > now:
            return
    # Okay, we know we're going to auto-respond to this sender, craft the
    # message, send it, and update the database.
    realname = mlist.real_name
    subject = _(
        'Auto-response for your message to the "$realname" mailing list')
    # Do string interpolation into the autoresponse text
    d = dict(listname       = realname,
             listurl        = mlist.script_url('listinfo'),
             requestemail   = mlist.request_address,
             owneremail     = mlist.owner_address,
             )
    if toadmin:
        rtext = mlist.autoresponse_admin_text
    elif torequest:
        rtext = mlist.autoresponse_request_text
    else:
        rtext = mlist.autoresponse_postings_text
    # Interpolation and Wrap the response text.
    text = Utils.wrap(Template(rtext).safe_substitute(d))
    outmsg = Message.UserNotification(sender, mlist.bounces_address,
                                      subject, text, mlist.preferred_language)
    outmsg['X-Mailer'] = _('The Mailman Replybot')
    # prevent recursions and mail loops!
    outmsg['X-Ack'] = 'No'
    outmsg.send(mlist)
    # update the grace period database
    if graceperiod > NODELTA:
        # graceperiod is in days, we need # of seconds
        quiet_until = now + graceperiod * 24 * 60 * 60
        if toadmin:
            mlist.admin_responses[sender] = quiet_until
        elif torequest:
            mlist.request_responses[sender] = quiet_until
        else:
            mlist.postings_responses[sender] = quiet_until



class Replybot:
    """Send automatic responses."""

    implements(IHandler)

    name = 'replybot'
    description = _('Send automatic responses.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        process(mlist, msg, msgdata)
