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

"""Send an acknowledgement of the successful post to the sender.

This only happens if the sender has set their AcknowledgePosts attribute.
This module must appear after the deliverer in the message pipeline in order
to send acks only after successful delivery.

"""

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Message
from Mailman.Handlers import HandlerAPI



def process(mlist, msg, msgdata):
    sender = msgdata.get('original_sender', msg.GetSender())
    sender = mlist.FindUser(sender)
    if sender and mlist.GetUserOption(sender, mm_cfg.AcknowledgePosts):
        subject = msg.getheader('subject')
        if subject:
            # trim off the subject prefix
            prefix = mlist.subject_prefix
            plen = len(prefix)
            if len(subject) > plen and subject[0:plen] == prefix:
                   subject = subject[plen:]
        # get the text from the template
        text = Utils.maketext(
            'postack.txt',
            {'subject'     : subject,
             'listname'    : mlist.real_name,
             'listinfo_url': mlist.GetScriptURL('listinfo', absolute=1),
             })
        # craft the outgoing message, with all headers and attributes
        # necessary for general delivery
        subject = '%s post acknowledgement' % mlist.real_name
        msg = Message.UserNotification(sender, mlist.GetAdminEmail(),
                                       subject, text)
        HandlerAPI.DeliverToUser(mlist, msg)
