# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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
interface which is more convenient for use inside Mailman.  It also supports
safe pickle deserialization, even if the email package adds additional Message
attributes.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Message',
    'OwnerNotification',
    'UserNotification',
    ]


import email
import email.message
import email.utils

from email.header import Header

from mailman.config import config


COMMASPACE = ', '
VERSION = tuple(int(v) for v in email.__version__.split('.'))



class Message(email.message.Message):
    def __init__(self):
        # We need a version number so that we can optimize __setstate__().
        self.__version__ = VERSION
        email.message.Message.__init__(self)

    def __getitem__(self, key):
        # Ensure that header values are unicodes.
        value = email.message.Message.__getitem__(self, key)
        if isinstance(value, str):
            return unicode(value, 'ascii')
        return value

    def get(self, name, failobj=None):
        # Ensure that header values are unicodes.
        value = email.message.Message.get(self, name, failobj)
        if isinstance(value, str):
            return unicode(value, 'ascii')
        return value

    def get_all(self, name, failobj=None):
        # Ensure all header values are unicodes.
        missing = object()
        all_values = email.message.Message.get_all(self, name, missing)
        if all_values is missing:
            return failobj
        return [(unicode(value, 'ascii') if isinstance(value, str) else value)
                for value in all_values]

    # BAW: For debugging w/ bin/dumpdb.  Apparently pprint uses repr.
    def __repr__(self):
        return self.__str__()

    def __setstate__(self, values):
        # The base class has grown and changed attributes over time.  This can
        # break messages sitting in Mailman's queues at the time of upgrading
        # the email package.  We can't (yet) change the email package to be
        # safer for pickling, so we handle such changes here.  Note that we're
        # using Python 2.6's email package version 4.0.1 as a base line here.
        self.__dict__ = values
        # The pickled instance should have an __version__ string, but it may
        # not if it's an email package message.
        version = values.get('__version__', (0, 0, 0))
        values['__version__'] = version
        # There's really nothing to check; there's nothing newer than email
        # 4.0.1 at the moment.

    @property
    def sender(self):
        """The address considered to be the author of the email.

        This is the first non-None value in the list of senders.

        :return: The email address of the first found sender, or the empty
            string if no sender address was found.
        :rtype: email address
        """
        for address in self.senders:
            # This could be None or the empty string.
            if address:
                return address
        return ''

    @property
    def senders(self):
        """Return a list of addresses representing the author of the email.

        The list will contain email addresses in the order determined by the
        configuration variable `sender_headers` in the `[mailman]` section.
        By default it uses this list of headers in order:

        1. From:
        2. envelope sender (i.e. From_, unixfrom, or RFC 2821 MAIL FROM)
        3. Reply-To:
        4. Sender:

        The return addresses are guaranteed to be lower case or None.  There
        may be more than four values in the returned list, since some of the
        originator headers above can appear multiple times in the message, or
        contain multiple values.

        :return: The list of email addresses that can be considered the sender
            of the message.
        :rtype: A list of email addresses or Nones
        """
        envelope_sender = self.get_unixfrom()
        senders = []
        for header in config.mailman.sender_headers.split():
            header = header.lower()
            if header == 'from_':
                senders.append(envelope_sender.lower()
                               if envelope_sender is not None
                               else '')
            else:
                field_values = self.get_all(header, [])
                senders.extend(address.lower() for (display_name, address)
                               in email.utils.getaddresses(field_values))
        # Filter out None and the empty string.
        return [sender for sender in senders if sender]

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

    def __init__(self, recipients, sender, subject=None, text=None, lang=None):
        Message.__init__(self)
        charset = (lang.charset if lang is not None else 'us-ascii')
        subject = ('(no subject)' if subject is None else subject)
        if text is not None:
            self.set_payload(text.encode(charset), charset)
        self['Subject'] = Header(subject.encode(charset), charset,
                                 header_name='Subject', errors='replace')
        self['From'] = sender
        if isinstance(recipients, (list, set, tuple)):
            self['To'] = COMMASPACE.join(recipients)
            self.recipients = recipients
        else:
            self['To'] = recipients
            self.recipients = set([recipients])

    def send(self, mlist, add_precedence=True, **_kws):
        """Sends the message by enqueuing it to the 'virgin' queue.

        This is used for all internally crafted messages.

        :param mlist: The mailing list to send the message to.
        :type mlist: `IMailingList`
        :param add_precedence: Flag indicating whether a `Precedence: bulk` 
            header should be added to the message or not.
        :type add_precedence: bool

        This function also accepts arbitrary keyword arguments.  The key/value
        pairs for **kws is added to the metadata dictionary associated with
        the enqueued message.
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
        if 'precedence' not in self and add_precedence:
            self['Precedence'] = 'bulk'
        self._enqueue(mlist, **_kws)

    def _enqueue(self, mlist, **_kws):
        # Not imported at module scope to avoid import loop
        virginq = config.switchboards['virgin']
        # The message metadata better have a 'recip' attribute.
        enqueue_kws = dict(
            recipients=self.recipients,
            nodecorate=True,
            reduced_list_headers=True,
            )
        if mlist is not None:
            enqueue_kws['listname'] = mlist.fqdn_listname
        enqueue_kws.update(_kws)
        # Keywords must be strings in Python 2.6.
        str_keywords = dict()
        for key, val in enqueue_kws.items():
            str_keywords[str(key)] = val
        virginq.enqueue(self, **str_keywords)



class OwnerNotification(UserNotification):
    """Like user notifications, but this message goes to some owners."""

    def __init__(self, mlist, subject=None, text=None, roster=None):
        if roster is None:
            recipients = set([config.mailman.site_owner])
            to = config.mailman.site_owner
        else:
            recipients = set(address.email for address in roster.addresses)
            to = mlist.owner_address
        sender = config.mailman.site_owner
        UserNotification.__init__(self, recipients, sender, subject,
                                  text, mlist.preferred_language)
        # Hack the To header to look like it's going to the -owner address
        del self['to']
        self['To'] = to
        self._sender = sender

    def _enqueue(self, mlist, **_kws):
        # Not imported at module scope to avoid import loop
        virginq = config.switchboards['virgin']
        # The message metadata better have a `recip' attribute
        virginq.enqueue(self,
                        listname=mlist.fqdn_listname,
                        recipients=self.recipients,
                        nodecorate=True,
                        reduced_list_headers=True,
                        envsender=self._sender,
                        **_kws)
