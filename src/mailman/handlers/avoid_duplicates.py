# Copyright (C) 2002-2012 by the Free Software Foundation, Inc.
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

"""If the user wishes it, do not send duplicates of the same message.

This module keeps an in-memory dictionary of Message-ID: and recipient pairs.
If a message with an identical Message-ID: is about to be sent to someone who
has already received a copy, we either drop the message, add a duplicate
warning header, or pass it through, depending on the user's preferences.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AvoidDuplicates',
    ]


from email.utils import getaddresses, formataddr
from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler


COMMASPACE = ', '



class AvoidDuplicates:
    """If the user wishes it, do not send duplicates of the same message."""

    implements(IHandler)

    name = 'avoid-duplicates'
    description = _('Suppress some duplicates of the same message.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        recips = msgdata.get('recipients')
        # Short circuit
        if not recips:
            return
        # Seed this set with addresses we don't care about dup avoiding.
        listaddrs = set((mlist.posting_address,
                         mlist.bounces_address,
                         mlist.owner_address,
                         mlist.request_address))
        explicit_recips = listaddrs.copy()
        # Figure out the set of explicit recipients.
        cc_addresses = {}
        for header in ('to', 'cc', 'resent-to', 'resent-cc'):
            addrs = getaddresses(msg.get_all(header, []))
            header_addresses = dict((addr, formataddr((name, addr)))
                                    for name, addr in addrs
                                    if addr)
            if header == 'cc':
                # Yes, it's possible that an address is mentioned in multiple
                # CC headers using different names.  In that case, the last
                # real name will win, but that doesn't seem like such a big
                # deal.  Besides, how else would you chose?
                cc_addresses.update(header_addresses)
            # Ignore the list addresses for purposes of dup avoidance.
            explicit_recips |= set(header_addresses)
        # Now strip out the list addresses.
        explicit_recips -= listaddrs
        if not explicit_recips:
            # No one was explicitly addressed, so we can't do any dup
            # collapsing
            return
        newrecips = set()
        for r in recips:
            # If this recipient is explicitly addressed...
            if r in explicit_recips:
                send_duplicate = True
                # If the member wants to receive duplicates, or if the
                # recipient is not a member at all, they will get a copy.
                # header.
                member = mlist.members.get_member(r)
                if member and not member.receive_list_copy:
                    send_duplicate = False
                # We'll send a duplicate unless the user doesn't wish it.  If
                # personalization is enabled, the add-dupe-header flag will
                # add a X-Mailman-Duplicate: yes header for this user's
                # message.
                if send_duplicate:
                    msgdata.setdefault('add-dup-header', set()).add(r)
                    newrecips.add(r)
                elif r in cc_addresses:
                    del cc_addresses[r]
            else:
                # Otherwise, this is the first time they've been in the recips
                # list.  Add them to the newrecips list and flag them as
                # having received this message.
                newrecips.add(r)
        # Set the new list of recipients.  XXX recips should always be a set.
        msgdata['recipients'] = list(newrecips)
        # RFC 2822 specifies zero or one CC header
        if cc_addresses:
            del msg['cc']
            msg['CC'] = COMMASPACE.join(cc_addresses.values())
