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

"""Standard Mailman message object.

This is a subclass of mimeo.Message but provides a slightly extended interface
which is more convenient for use inside Mailman.
"""

from types import ListType

import mimelib.Message
from mimelib.StringableMixin import StringableMixin
from mimelib.address import getaddresses

from Mailman import mm_cfg

COMMASPACE = ', '



class Message(mimelib.Message.Message, StringableMixin):
    def get_sender(self, use_envelope=None, preserve_case=0):
        """Return the address considered to be the author of the email.

        This can return either the From: header, the Sender: header or the
        envelope header (a.k.a. the unixfrom header).  The first non-empty
        header value found is returned.  However the search order is
        determined by the following:

        - If mm_cfg.USE_ENVELOPE_SENDER is true, then the search order is
          Sender:, From:, unixfrom

        - Otherwise, the search order is From:, Sender:, unixfrom

        The optional argument use_envelope, if given overrides the
        mm_cfg.USE_ENVELOPE_SENDER setting.  It should be set to either 0 or 1
        (don't use None since that indicates no-override).

        unixfrom should never be empty.  The return address is always
        lowercased, unless preserve_case is true.
        """
        senderfirst = mm_cfg.USE_ENVELOPE_SENDER
        if use_envelope is not None:
            senderfirst = use_envelope
        if senderfirst:
            headers = ('sender', 'from')
        else:
            headers = ('from', 'sender')
        for h in headers:
            # Use only the first occurrance of Sender: or From:, although it's
            # not likely there will be more than one.
            addrs = getaddresses([self[h]])
            realname, address = addrs[0]
            if address:
                break
        else:
            # We didn't find a non-empty header, so let's fall back to the
            # unixfrom address.  This should never be empty, but if it ever
            # is, it's probably a Really Bad Thing.  Further, we just assume
            # that if the unixfrom exists, the second field is the address.
            unixfrom = self.get_unixfrom()
            if unixfrom:
                address = unixfrom.split()[1]
            else:
                # TBD: now what?!
                address = ''
        if not preserve_case:
            address = address.lower()
        return address



class UserNotification(Message):
    """Class for internally crafted messages."""

    def __init__(self, recip, sender, subject=None, text=None):
        Message.__init__(self)
        if text is not None:
            self.set_payload(text)
        if subject is None:
            subject = '(no subject)'
        self['Subject'] = subject
        self['From'] = sender
        if isinstance(recip, ListType):
            self['To'] = COMMASPACE.join(recip)
            self.recips = recip
        else:
            self['To'] = recip
            self.recips = [recip]

    def send(self, mlist, **_kws):
        """Prepares the message for sending by enqueing it to the `virgin'
        queue.

        This is used for all internally crafted messages.
        """
        # Not imported at module scope to avoid import loop
        from Mailman.Queue.sbcache import get_switchboard
        virginq = get_switchboard(mm_cfg.VIRGINQUEUE_DIR)
        # The message metadata better have a `recip' attribute
        virginq.enqueue(self,
                        listname = mlist.internal_name(),
                        recips = self.recips,
                        **_kws)
