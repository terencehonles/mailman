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

"""Calculate the regular (i.e. non-digest) recipients of the message.

This module calculates the non-digest recipients for the message based on the
list's membership and configuration options.  It places the list of recipients
on the `recips' attribute of the message.  This attribute is used by the
SendmailDeliver and BulkDeliver modules.

"""

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Message
from Mailman.i18n import _
from Mailman.Errors import RejectMessage
from Mailman.Logging.Syslog import syslog



class RejectUrgentMessage(RejectMessage):
    def __init__(self, mlist, msg):
        self._realname = mlist.real_name
        self._subject = msg['subject'] or _('(no subject)')

    def subject(self):
        return _('Your urgent message was rejected')

    def details(self):
        # Do it this way for i18n.
        realname = self._realname
        subject = self._subject
        txt = _("""\
Your urgent message to the %(realname)s mailing list was not authorized for
delivery.  The original message as received by Mailman is attached.

""")
        return Utils.wrap(txt)



def process(mlist, msg, msgdata):
    # Short circuit if we've already calculated the recipients list,
    # regardless of whether the list is empty or not.
    if msgdata.has_key('recips'):
        return
    # Support for urgent messages, which bypasses digests and disabled
    # delivery and forces an immediate delivery to all members Right Now.  We
    # are specifically /not/ allowing the site admins password to work here
    # because we want to discourage the practice of sending the site admin
    # password through email in the clear. (see also Approve.py)
    missing = []
    password = msg.get('urgent', missing)
    if password is not missing:
        if mlist.Authenticate((mm_cfg.AuthListModerator,
                               mm_cfg.AuthListAdmin),
                              password):
            recips = mlist.GetDeliveryMembers() + \
                     mlist.GetDigestDeliveryMembers()
            msgdata['recips'] = recips
            return
        else:
            # Bad Urgent: password, so hold it instead of passing it on.  I
            # think it's better that the sender know they screwed up than to
            # deliver it normally.
            raise RejectUrgentMessage(mlist, msg)
    # Normal delivery to the regular members.
    dont_send_to_sender = 0
    # Get the membership address of the sender, if a member.  Then get the
    # sender's receive-own-posts option
    sender = mlist.FindUser(msg.get_sender())
    if sender and mlist.GetUserOption(sender, mm_cfg.DontReceiveOwnPosts):
        dont_send_to_sender = 1
    # Calculate the regular recipients of the message
    members = mlist.GetDeliveryMembers()
    recips = [m for m in members
              if not mlist.GetUserOption(m, mm_cfg.DisableDelivery)]
    # Remove the sender if they don't want to receive their own posts
    if dont_send_to_sender:
        try:
            recips.remove(mlist.GetUserSubscribedAddress(sender))
        except ValueError:
            # Sender does not want to get copies of their own messages (not
            # metoo), but delivery to their address is disabled (nomail)
            pass
    # Bookkeeping
    msgdata['recips'] = recips
