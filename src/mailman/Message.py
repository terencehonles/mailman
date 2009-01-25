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

"""Standard Mailman message object.

This is a subclass of email.message.Message but provides a slightly extended
interface which is more convenient for use inside Mailman.
"""

import re
import email
import email.message
import email.utils

from email.charset import Charset
from email.header import Header
from lazr.config import as_boolean

from mailman import Utils
from mailman.config import config

COMMASPACE = ', '

mo = re.match(r'([\d.]+)', email.__version__)
VERSION = tuple(int(s) for s in mo.group().split('.'))



class Message(email.message.Message):
    def __init__(self):
        # We need a version number so that we can optimize __setstate__()
        self.__version__ = VERSION
        email.message.Message.__init__(self)

    def __getitem__(self, key):
        value = email.message.Message.__getitem__(self, key)
        if isinstance(value, str):
            return unicode(value, 'ascii')
        return value

    def get(self, name, failobj=None):
        value = email.message.Message.get(self, name, failobj)
        if isinstance(value, str):
            return unicode(value, 'ascii')
        return value

    def get_all(self, name, failobj=None):
        missing = object()
        all_values = email.message.Message.get_all(self, name, missing)
        if all_values is missing:
            return failobj
        return [(unicode(value, 'ascii') if isinstance(value, str) else value)
                for value in all_values]

    # BAW: For debugging w/ bin/dumpdb.  Apparently pprint uses repr.
    def __repr__(self):
        return self.__str__()

    def __setstate__(self, d):
        # The base class attributes have changed over time.  Which could
        # affect Mailman if messages are sitting in the queue at the time of
        # upgrading the email package.  We shouldn't burden email with this,
        # so we handle schema updates here.
        self.__dict__ = d
        # We know that email 2.4.3 is up-to-date
        version = d.get('__version__', (0, 0, 0))
        d['__version__'] = VERSION
        if version >= VERSION:
            return
        # Messages grew a _charset attribute between email version 0.97 and 1.1
        if not d.has_key('_charset'):
            self._charset = None
        # Messages grew a _default_type attribute between v2.1 and v2.2
        if not d.has_key('_default_type'):
            # We really have no idea whether this message object is contained
            # inside a multipart/digest or not, so I think this is the best we
            # can do.
            self._default_type = 'text/plain'
        # Header instances used to allow both strings and Charsets in their
        # _chunks, but by email 2.4.3 now it's just Charsets.
        headers = []
        hchanged = 0
        for k, v in self._headers:
            if isinstance(v, Header):
                chunks = []
                cchanged = 0
                for s, charset in v._chunks:
                    if isinstance(charset, str):
                        charset = Charset(charset)
                        cchanged = 1
                    chunks.append((s, charset))
                if cchanged:
                    v._chunks = chunks
                    hchanged = 1
            headers.append((k, v))
        if hchanged:
            self._headers = headers

    # I think this method ought to eventually be deprecated
    def get_sender(self):
        """Return the address considered to be the author of the email.

        This can return either the From: header, the Sender: header or the
        envelope header (a.k.a. the unixfrom header).  The first non-empty
        header value found is returned.  However the search order is
        determined by the following:

        - If config.mailman.use_envelope_sender is true, then the search order
          is Sender:, From:, unixfrom

        - Otherwise, the search order is From:, Sender:, unixfrom

        unixfrom should never be empty.  The return address is always
        lower cased.

        This method differs from get_senders() in that it returns one and only
        one address, and uses a different search order.
        """
        senderfirst = as_boolean(config.mailman.use_envelope_sender)
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
            addrs = email.utils.getaddresses([fieldval])
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
        return address.lower()

    def get_senders(self):
        """Return a list of addresses representing the author of the email.

        The list will contain the following addresses (in order)
        depending on availability:

        1. From:
        2. unixfrom (From_)
        3. Reply-To:
        4. Sender:

        The return addresses are always lower cased.
        """
        pairs = []
        for header in config.mailman.sender_headers.split():
            header = header.lower()
            if header == 'from_':
                # get_unixfrom() returns None if there's no envelope
                unix_from = self.get_unixfrom()
                fieldval = (unix_from if unix_from is not None else '')
                try:
                    pairs.append(('', fieldval.split()[1]))
                except IndexError:
                    # Ignore badly formatted unixfroms
                    pass
            else:
                fieldvals = self.get_all(header)
                if fieldvals:
                    pairs.extend(email.utils.getaddresses(fieldvals))
        authors = []
        for pair in pairs:
            address = pair[1]
            if address is not None:
                address = address.lower()
            authors.append(address)
        return authors

    def get_filename(self, failobj=None):
        """Some MUA have bugs in RFC2231 filename encoding and cause
        Mailman to stop delivery in Scrubber.py (called from ToDigest.py).
        """
        try:
            filename = email.message.Message.get_filename(self, failobj)
            return filename
        except (UnicodeError, LookupError, ValueError):
            return failobj



class UserNotification(Message):
    """Class for internally crafted messages."""

    def __init__(self, recip, sender, subject=None, text=None, lang=None):
        Message.__init__(self)
        charset = 'us-ascii'
        if lang is not None:
            charset = Utils.GetCharSet(lang)
        if text is not None:
            self.set_payload(text.encode(charset), charset)
        if subject is None:
            subject = '(no subject)'
        self['Subject'] = Header(subject.encode(charset), charset,
                                 header_name='Subject', errors='replace')
        self['From'] = sender
        if isinstance(recip, list):
            self['To'] = COMMASPACE.join(recip)
            self.recips = recip
        else:
            self['To'] = recip
            self.recips = [recip]

    def send(self, mlist, **_kws):
        """Sends the message by enqueuing it to the 'virgin' queue.

        This is used for all internally crafted messages.
        """
        # Since we're crafting the message from whole cloth, let's make sure
        # this message has a Message-ID.
        if 'message-id' not in self:
            self['Message-ID'] = email.utils.make_msgid()
        # Ditto for Date: as required by RFC 2822.
        if 'date' not in self:
            self['Date'] = email.utils.formatdate(localtime=True)
        # UserNotifications are typically for admin messages, and for messages
        # other than list explosions.  Send these out as Precedence: bulk, but
        # don't override an existing Precedence: header.
        if 'precedence' not in self:
            self['Precedence'] = 'bulk'
        self._enqueue(mlist, **_kws)

    def _enqueue(self, mlist, **_kws):
        # Not imported at module scope to avoid import loop
        virginq = config.switchboards['virgin']
        # The message metadata better have a 'recip' attribute.
        enqueue_kws = dict(
            recips=self.recips,
            nodecorate=True,
            reduced_list_headers=True,
            )
        if mlist is not None:
            enqueue_kws['listname'] = mlist.fqdn_listname
        enqueue_kws.update(_kws)
        virginq.enqueue(self, **enqueue_kws)



class OwnerNotification(UserNotification):
    """Like user notifications, but this message goes to the list owners."""

    def __init__(self, mlist, subject=None, text=None, tomoderators=True):
        if tomoderators:
            roster = mlist.moderators
        else:
            roster = mlist.owners
        recips = [address.address for address in roster.addresses]
        sender = config.mailman.site_owner
        lang = mlist.preferred_language
        UserNotification.__init__(self, recips, sender, subject, text, lang)
        # Hack the To header to look like it's going to the -owner address
        del self['to']
        self['To'] = mlist.owner_address
        self._sender = sender

    def _enqueue(self, mlist, **_kws):
        # Not imported at module scope to avoid import loop
        virginq = config.switchboards['virgin']
        # The message metadata better have a `recip' attribute
        virginq.enqueue(self,
                        listname=mlist.fqdn_listname,
                        recips=self.recips,
                        nodecorate=True,
                        reduced_list_headers=True,
                        envsender=self._sender,
                        **_kws)
