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

"""Send an acknowledgement of the successful post to the sender.

This only happens if the sender has set their AcknowlegePosts attribute.  This
module must appear after the deliverer in the message pipeline in order to
send acks only after successful delivery.

"""

from Mailman import Utils



def process(mlist, msg):
    sender = mlist.FindUser(msg.GetSender())
    if sender and mlist.GetUserOption(sender, mm_cfg.AcknowlegePosts):
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
             'listname'    : self.real_name,
             'listinfo_url': self.GetAbsoluteScriptURL('listinfo'),
             })
        # TBD: we should send the message to the admin using the same
        # mechanism used to post messages to the list (e.g. if we're doing
        # sendmail injection, we should use it for all sent messages)
        self.SendTextToUser('%s post acknowlegement' % mlist.real_name,
                            text, sender)
