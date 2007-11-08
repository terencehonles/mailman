# Copyright (C) 1998-2007 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Standard Mailman message object.

This is a subclass of mimeo.Message but provides a slightly extended interface
which is more convenient for use inside Mailman.
"""

import re
import email
import email.message
import email.utils

from email.charset import Charset
from email.header import Header

from Mailman import Utils
from Mailman.configuration import config

COMMASPACE = ', '

mo = re.match(r'([\d.]+)', email.__version__)
VERSION = tuple([int(s) for s in mo.group().split('.')])



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

    def get_all(self, name, failobj=None):
        all_values = email.message.Message.get_all(self, name, failobj)
        return [unicode(value, 'ascii') for value in all_values]

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
    def get_sender(self, use_envelope=None, preserve_case=0):
        """Return the address considered to be the author of the email.

        This can return either the From: header, the Sender: header or the
        envelope header (a.k.a. the unixfrom header).  The first non-empty
        header value found is returned.  However the search order is
        determined by the following:

        - If config.USE_ENVELOPE_SENDER is true, then the search order is
          Sender:, From:, unixfrom

        - Otherwise, the search order is From:, Sender:, unixfrom

        The optional argument use_envelope, if given overrides the
        config.USE_ENVELOPE_SENDER setting.  It should be set to either 0 or 1
        (don't use None since that indicates no-override).

        unixfrom should never be empty.  The return address is always
        lowercased, unless preserve_case is true.

        This method differs from get_senders() in that it returns one and only
        one address, and uses a different search order.
        """
        senderfirst = config.USE_ENVELOPE_SENDER
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
            headers = config.SENDER_HEADERS
        pairs = []
        for h in headers:
            if h is None:
                # get_unixfrom() returns None if there's no envelope
                fieldval = self.get_unixfrom() or ''
                try:
                    pairs.append(('', fieldval.split()[1]))
                except IndexError:
                    # Ignore badly formatted unixfroms
                    pass
            else:
                fieldvals = self.get_all(h)
                if fieldvals:
                    pairs.extend(email.utils.getaddresses(fieldvals))
        authors = []
        for pair in pairs:
            address = pair[1]
            if address is not None and not preserve_case:
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
        # this message has a Message-ID.  Yes, the MTA would give us one, but
        # this is useful for logging to logs/smtp.
        if 'message-id' not in self:
            self['Message-ID'] = email.utils.make_msgid()
        # Ditto for Date: which is required by RFC 2822
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
        from Mailman.queue import Switchboard
        virginq = Switchboard(config.VIRGINQUEUE_DIR)
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
        sender = config.SITE_OWNER_ADDRESS
        lang = mlist.preferred_language
        UserNotification.__init__(self, recips, sender, subject, text, lang)
        # Hack the To header to look like it's going to the -owner address
        del self['to']
        self['To'] = mlist.owner_address
        self._sender = sender

    def _enqueue(self, mlist, **_kws):
        # Not imported at module scope to avoid import loop
        from Mailman.queue import Switchboard
        virginq = Switchboard(config.VIRGINQUEUE_DIR)
        # The message metadata better have a `recip' attribute
        virginq.enqueue(self,
                        listname=mlist.fqdn_listname,
                        recips=self.recips,
                        nodecorate=True,
                        reduced_list_headers=True,
                        envsender=self._sender,
                        **_kws)
