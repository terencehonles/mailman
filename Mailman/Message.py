# Copyright (C) 1998,1999,2000,2001,2002 by the Free Software Foundation, Inc.
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

import email.Message
import email.Utils

from email.Charset import Charset
from email.Header import Header

from types import ListType

from Mailman import mm_cfg
from Mailman import Utils

COMMASPACE = ', '



class Message(email.Message.Message):
    # BAW: For debugging w/ bin/dumpdb.  Apparently pprint uses repr.
    def __repr__(self):
        return self.__str__()

    def __setstate__(self, d):
        # The pickle format has changed between email version 0.97 and 1.1
        self.__dict__ = d
        if not d.has_key('_charset'):
            self._charset = None

    # I think this method ought to eventually be deprecated
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

        This method differs from get_senders() in that it returns one and only
        one address, and uses a different search order.
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
            fieldval = self[h]
            if not fieldval:
                continue
            addrs = email.Utils.getaddresses([fieldval])
            try:
                realname, address = addrs[0]
            except IndexError:
                continue
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
            return address.lower()
        return address

    def get_senders(self, preserve_case=0, headers=None):
        """Return a list of addresses representing the author of the email.

        The list will contain the following addresses (in order)
        depending on availability:

        1. From:
        2. unixfrom
        3. Reply-To:
        4. Sender:

        The return addresses are always lower cased, unless `preserve_case' is
        true.  Optional `headers' gives an alternative search order, with None
        meaning, search the unixfrom header.  Items in `headers' are field
        names without the trailing colon.
        """
        if headers is None:
            headers = ('from', None, 'reply-to', 'sender')
        pairs = []
        for h in headers:
            if h is None:
                fieldval = self.get_unixfrom()
                try:
                    pairs.append(fieldval.split()[1])
                except IndexError:
                    # Ignore badly formatted unixfroms
                    pass
            else:
                fieldval = self[h]
                if fieldval:
                    pairs.extend(email.Utils.getaddresses([fieldval]))
        authors = []
        for pair in pairs:
            address = pair[1]
            if address is not None and not preserve_case:
                address = address.lower()
            authors.append(address)
        return authors



class UserNotification(Message):
    """Class for internally crafted messages."""

    def __init__(self, recip, sender, subject=None, text=None, lang=None):
        Message.__init__(self)
        charset = None
        if lang is not None:
            charset = Charset(Utils.GetCharSet(lang))
        if text is not None:
            self.set_payload(text, charset)
        if subject is None:
            subject = '(no subject)'
        self['Subject'] = Header(subject, charset, header_name='Subject')
        self['From'] = sender
        if isinstance(recip, ListType):
            self['To'] = COMMASPACE.join(recip)
            self.recips = recip
        else:
            self['To'] = recip
            self.recips = [recip]

    def send(self, mlist, **_kws):
        """Sends the message by enqueuing it to the `virgin' queue.

        This is used for all internally crafted messages.
        """
        # Since we're crafting the message from whole cloth, let's make sure
        # this message has a Message-ID.  Yes, the MTA would give us one, but
        # this is useful for logging to logs/smtp.
        if not self.has_key('message-id'):
            self['Message-ID'] = Utils.unique_message_id(mlist)
        # Ditto for Date: which is required by RFC 2822
        if not self.has_key('date'):
            self['Date'] = email.Utils.formatdate(localtime=1)
        # Not imported at module scope to avoid import loop
        from Mailman.Queue.sbcache import get_switchboard
        virginq = get_switchboard(mm_cfg.VIRGINQUEUE_DIR)
        # The message metadata better have a `recip' attribute
        virginq.enqueue(self,
                        listname = mlist.internal_name(),
                        recips = self.recips,
                        nodecorate = 1,
                        **_kws)
