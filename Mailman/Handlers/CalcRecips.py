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

"""Calculate the regular (i.e. non-digest) recipients of the message.

This module calculates the non-digest recipients for the message based on the
list's membership and configuration options.  It places the list of recipients
on the `recips' attribute of the message.  This attribute is used by the
SendmailDeliver and BulkDeliver modules.

"""

from Mailman import mm_cfg



def process(mlist, msg):
    # yes, short circuit if the message object already has a recipients
    # attribute, regardless of whether the list is empty or not.
    if hasattr(msg, 'recips'):
        return
    dont_send_to_sender = 0
    # Get the membership address of the sender, if a member.  Then get the
    # sender's receive-own-posts option
    sender = mlist.FindUser(msg.GetSender())
    if sender and mlist.GetUserOption(sender, mm_cfg.DontReceiveOwnPosts):
        dont_send_to_sender = 1
    # calculate the regular recipients of the message
    members = mlist.GetDeliveryMembers()
    recips = []
    for m in members:
        if not mlist.GetUserOption(m, mm_cfg.DisableDelivery):
            recips.append(m)
    # remove the sender if they don't want to receive
    if dont_send_to_sender:
        try:
            recips.remove(mlist.GetUserSubscribedAddress(sender))
        except ValueError:
            # sender does not want to get copies of their own messages
            # (not metoo), but delivery to their address is disabled (nomail)
            pass
    # bookkeeping
    msg.recips = recips
