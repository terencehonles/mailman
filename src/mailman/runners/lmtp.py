# Copyright (C) 2006-2012 by the Free Software Foundation, Inc.
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

"""Mailman LMTP runner (server).

Most mail servers can be configured to deliver local messages via 'LMTP'[1].
This module is actually an LMTP server rather than a standard runner.

The LMTP runner opens a local TCP port and waits for the mail server to
connect to it.  The messages it receives over LMTP are very minimally parsed
for sanity and if they look okay, they are accepted and injected into
Mailman's incoming queue for normal processing.  If they don't look good, or
are destined for a bogus sub-address, they are rejected right away, hopefully
so that the peer mail server can provide better diagnostics.

[1] RFC 2033 Local Mail Transport Protocol
    http://www.faqs.org/rfcs/rfc2033.html
"""

import email
import smtpd
import logging
import asyncore

from email.utils import parseaddr
from zope.component import getUtility

from mailman.config import config
from mailman.core.runner import Runner
from mailman.database.transaction import txn
from mailman.email.message import Message
from mailman.interfaces.listmanager import IListManager
from mailman.utilities.email import add_message_hash

elog = logging.getLogger('mailman.error')
qlog = logging.getLogger('mailman.runner')
slog = logging.getLogger('mailman.smtp')


# We only care about the listname and the sub-addresses as in listname@ or
# listname-request@.  This maps user visible subaddress names (which may
# include aliases) to the internal canonical subaddress name.
SUBADDRESS_NAMES = dict(
    admin='bounces',
    bounces='bounces',
    confirm='confirm',
    join='join',
    leave='leave',
    owner='owner',
    request='request',
    subscribe='join',
    unsubscribe='leave',
    )

# This maps subaddress canonical name to the destination queue that handles
# messages sent to that subaddress.
SUBADDRESS_QUEUES = dict(
    bounces='bounces',
    confirm='command',
    join='command',
    leave='command',
    owner='in',
    request='command',
    )

DASH    = '-'
CRLF    = '\r\n'
ERR_451 = '451 Requested action aborted: error in processing'
ERR_501 = '501 Message has defects'
ERR_502 = '502 Error: command HELO not implemented'
ERR_550 = '550 Requested action not taken: mailbox unavailable'
ERR_550_MID = '550 No Message-ID header provided'

# XXX Blech
smtpd.__version__ = 'Python LMTP runner 1.0'



def split_recipient(address):
    """Split an address into listname, subaddress and domain parts.

    For example:

    >>> split_recipient('mylist@example.com')
    ('mylist', None, 'example.com')

    >>> split_recipient('mylist-request@example.com')
    ('mylist', 'request', 'example.com')

    :param address: The destination address.
    :return: A 3-tuple of the form (list-shortname, subaddress, domain).
        subaddress may be None if this is the list's posting address.
    """
    localpart, domain = address.split('@', 1)
    localpart = localpart.split(config.mta.verp_delimiter, 1)[0]
    parts = localpart.split(DASH)
    if parts[-1] in SUBADDRESS_NAMES:
        listname = DASH.join(parts[:-1])
        subaddress = parts[-1]
    else:
        listname = localpart
        subaddress = None
    return listname, subaddress, domain



class Channel(smtpd.SMTPChannel):
    """An LMTP channel."""

    def __init__(self, server, conn, addr):
        smtpd.SMTPChannel.__init__(self, server, conn, addr)
        # Stash this here since the subclass uses private attributes. :(
        self._server = server

    def smtp_LHLO(self, arg):
        """The LMTP greeting, used instead of HELO/EHLO."""
        smtpd.SMTPChannel.smtp_HELO(self, arg)

    def smtp_HELO(self, arg):
        """HELO is not a valid LMTP command."""
        self.push(ERR_502)



class LMTPRunner(Runner, smtpd.SMTPServer):
    # Only __init__ is called on startup. Asyncore is responsible for later
    # connections from the MTA.  slice and numslices are ignored and are
    # necessary only to satisfy the API.
    def __init__(self, slice=None, numslices=1):
        localaddr = config.mta.lmtp_host, int(config.mta.lmtp_port)
        # Do not call Runner's constructor because there's no QDIR to create
        qlog.debug('LMTP server listening on %s:%s',
                   localaddr[0], localaddr[1])
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr=None)

    def handle_accept(self):
        conn, addr = self.accept()
        Channel(self, conn, addr)
        slog.debug('LMTP accept from %s', addr)

    @txn
    def process_message(self, peer, mailfrom, rcpttos, data):
        try:
            # Refresh the list of list names every time we process a message
            # since the set of mailing lists could have changed.
            listnames = set(getUtility(IListManager).names)
            # Parse the message data.  If there are any defects in the
            # message, reject it right away; it's probably spam.
            msg = email.message_from_string(data, Message)
        except Exception:
            elog.exception('LMTP message parsing')
            config.db.abort()
            return CRLF.join(ERR_451 for to in rcpttos)
        # Do basic post-processing of the message, checking it for defects or
        # other missing information.
        message_id = msg.get('message-id')
        if message_id is None:
            return ERR_550_MID
        if msg.defects:
            return ERR_501
        msg.original_size = len(data)
        add_message_hash(msg)
        msg['X-MailFrom'] = mailfrom
        # RFC 2033 requires us to return a status code for every recipient.
        status = []
        # Now for each address in the recipients, parse the address to first
        # see if it's destined for a valid mailing list.  If so, then queue
        # the message to the appropriate place and record a 250 status for
        # that recipient.  If not, record a failure status for that recipient.
        for to in rcpttos:
            try:
                to = parseaddr(to)[1].lower()
                listname, subaddress, domain = split_recipient(to)
                slog.debug('%s to: %s, list: %s, sub: %s, dom: %s',
                           message_id, to, listname, subaddress, domain)
                listname += '@' + domain
                if listname not in listnames:
                    status.append(ERR_550)
                    continue
                # The recipient is a valid mailing list.  Find the subaddress
                # if there is one, and set things up to enqueue to the proper
                # queue.
                queue = None
                msgdata = dict(listname=listname,
                               original_size=msg.original_size)
                canonical_subaddress = SUBADDRESS_NAMES.get(subaddress)
                queue = SUBADDRESS_QUEUES.get(canonical_subaddress)
                if subaddress is None:
                    # The message is destined for the mailing list.
                    msgdata['to_list'] = True
                    queue = 'in'
                elif canonical_subaddress is None:
                    # The subaddress was bogus.
                    slog.error('%s unknown sub-address: %s',
                               message_id, subaddress)
                    status.append(ERR_550)
                    continue
                else:
                    # A valid subaddress.
                    msgdata['subaddress'] = canonical_subaddress
                    if canonical_subaddress == 'owner':
                        msgdata.update(dict(
                            to_owner=True,
                            envsender=config.mailman.site_owner,
                            ))
                        queue = 'in'
                # If we found a valid destination, enqueue the message and add
                # a success status for this recipient.
                if queue is not None:
                    config.switchboards[queue].enqueue(msg, msgdata)
                    slog.debug('%s subaddress: %s, queue: %s',
                               message_id, canonical_subaddress, queue)
                    status.append('250 Ok')
            except Exception:
                slog.exception('Queue detection: %s', msg['message-id'])
                config.db.abort()
                status.append(ERR_550)
        # All done; returning this big status string should give the expected
        # response to the LMTP client.
        return CRLF.join(status)

    def run(self):
        """See `IRunner`."""
        asyncore.loop()

    def stop(self):
        """See `IRunner`."""
        asyncore.socket_map.clear()
        asyncore.close_all()
        self.close()
