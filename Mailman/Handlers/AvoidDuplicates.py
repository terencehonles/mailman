# Copyright (C) 2002 by the Free Software Foundation, Inc.
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

"""If the user wishes it, do not send duplicates of the same message.

This module keeps an in-memory dictionary of Message-ID: and recipient pairs.
If a message with an identical Message-ID: is about to be sent to someone who
has already received a copy, we either drop the message, add a duplicate
warning header, or pass it through, depending on the user's preferences.
"""

from Mailman import mm_cfg

from email.Utils import getaddresses



def process(mlist, msg, msgdata):
    recips = msgdata['recips']
    # Short circuit
    if not recips:
        return
    # Figure out the set of explicit recipients
    explicit_recips = {}
    for header in ('to', 'cc', 'resent-to', 'resent-cc'):
        for name, addr in getaddresses(msg.get_all(header, [])):
            if not addr:
                continue
            explicit_recips[addr] = 1
    if not explicit_recips:
        # No one was explicitly addressed, so we can do any dup collapsing
        return
    newrecips = []
    for r in recips:
        # If this recipient is explicitly addressed...
        if explicit_recips.has_key(r):
            send_duplicate = 1
            # If the member wants to receive duplicates, or if the recipient
            # is not a member at all, just flag the X-Mailman-Duplicate: yes
            # header.
            if mlist.isMember(r) and \
                   mlist.getMemberOption(r, mm_cfg.DontReceiveDuplicates):
                send_duplicate = 0
            # We'll send a duplicate unless the user doesn't wish it.  If
            # personalization is enabled, the add-dupe-header flag will add a
            # X-Mailman-Duplicate: yes header for this user's message.
            if send_duplicate:
                msgdata.setdefault('add-dup-header', {})[r] = 1
                newrecips.append(r)
        else:
            # Otherwise, this is the first time they've been in the recips
            # list.  Add them to the newrecips list and flag them as having
            # received this message.
            newrecips.append(r)
    # Set the new list of recipients
    msgdata['recips'] = newrecips
