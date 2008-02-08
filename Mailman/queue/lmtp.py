# Copyright (C) 2006-2008 by the Free Software Foundation, Inc.
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

"""Mailman LMTP runner (server).

Most mail servers can be configured to deliver local messages via 'LMTP'[1].
This module is actually an LMTP server rather than a standard queue runner.
Once it enters its main asyncore loop, it does not respond to mailmanctl
signals the same way as other runners do.  All signals will kill this process,
but the normal mailmanctl watchdog will restart it upon exit.

The LMTP runner opens a local TCP port and waits for the mail server to
connect to it.  The messages it receives over LMTP are very minimally parsed
for sanity and if they look okay, they are accepted and injected into
Mailman's incoming queue for processing through the normal pipeline.  If they
don't look good, or are destined for a bogus sub-queue address, they are
rejected right away, hopefully so that the peer mail server can provide better
diagnostics.

[1] RFC 2033 Local Mail Transport Protocol
    http://www.faqs.org/rfcs/rfc2033.html

See the variable USE_LMTP in Defaults.py.in for enabling this delivery
mechanism.
"""

# NOTE: LMTP delivery is experimental in Mailman 2.2.

import os
import email
import smtpd
import logging
import asyncore

from email.utils import parseaddr

from Mailman.Message import Message
from Mailman.configuration import config
from Mailman.runner import Runner, Switchboard

elog = logging.getLogger('mailman.error')
qlog = logging.getLogger('mailman.qrunner')

# We only care about the listname and the subq as in listname@ or
# listname-request@
subqnames = (
    'bounces',  'confirm',  'join', '       leave',
    'owner',    'request',  'subscribe',    'unsubscribe',
    )

DASH    = '-'
CRLF    = '\r\n'
ERR_451 = '451 Requested action aborted: error in processing'
ERR_502 = '502 Error: command HELO not implemented'
ERR_550 = config.LMTP_ERR_550

# XXX Blech
smtpd.__version__ = 'Python LMTP queue runner 1.0'



def getlistq(address):
    localpart, domain = address.split('@', 1)
    localpart = localpart.split(config.VERP_DELIMITER, 1)[0]
    l = localpart.split(DASH)
    if l[-1] in subqnames:
        listname = DASH.join(l[:-1])
        subq = l[-1]
    else:
        listname = localpart
        subq = None
    return listname, subq, domain



class SMTPChannel(smtpd.SMTPChannel):
    # Override smtpd.SMTPChannel don't can't change the class name so that we
    # don't have to reverse engineer Python's name mangling scheme.
    #
    # LMTP greeting is LHLO and no HELO/EHLO

    def smtp_LHLO(self, arg):
        smtpd.SMTPChannel.smtp_HELO(self, arg)

    def smtp_HELO(self, arg):
        self.push(ERR_502)



class LMTPRunner(Runner, smtpd.SMTPServer):
    # Only __init__ is called on startup. Asyncore is responsible for later
    # connections from MTA.   slice and numslices are ignored and are
    # necessary only to satisfy the API.
    def __init__(self, slice=None, numslices=1):
        localaddr = config.LMTP_HOST, config.LMTP_PORT
        # Do not call Runner's constructor because there's no QDIR to create
        smtpd.SMTPServer.__init__(self, localaddr, remoteaddr=None)

    def handle_accept(self):
        conn, addr = self.accept()
        channel = SMTPChannel(self, conn, addr)

    def process_message(self, peer, mailfrom, rcpttos, data):
        try:
            # Refresh the list of list names every time we process a message
            # since the set of mailing lists could have changed.  However, on
            # a big site this could be fairly expensive, so we may need to
            # cache this in some way.
            listnames = set(config.list_manager.names)
            # Parse the message data.  XXX Should we reject the message
            # immediately if it has defects?  Usually only spam has defects.
            msg = email.message_from_string(data, Message)
            msg['X-MailFrom'] = mailfrom
        except Exception, e:
            elog.error('%s', e)
            return CRLF.join([ERR_451 for to in rcpttos])
        # RFC 2033 requires us to return a status code for every recipient.
        status = []
        # Now for each address in the recipients, parse the address to first
        # see if it's destined for a valid mailing list.  If so, then queue
        # the message to the appropriate place and record a 250 status for
        # that recipient.  If not, record a failure status for that recipient.
        for to in rcpttos:
            try:
                to = parseaddr(to)[1].lower()
                listname, subq, domain = getlistq(to)
                listname += '@' + domain
                if listname not in listnames:
                    status.append(ERR_550)
                    continue
                # The recipient is a valid mailing list; see if it's a valid
                # sub-queue, and if so, enqueue it.
                msgdata = dict(listname=listname)
                if subq in ('bounces', 'admin'):
                    queue = Switchboard(config.BOUNCEQUEUE_DIR)
                elif subq == 'confirm':
                    msgdata['toconfirm'] = True
                    queue = Switchboard(config.CMDQUEUE_DIR)
                elif subq in ('join', 'subscribe'):
                    msgdata['tojoin'] = True
                    queue = Switchboard(config.CMDQUEUE_DIR)
                elif subq in ('leave', 'unsubscribe'):
                    msgdata['toleave'] = True
                    queue = Switchboard(config.CMDQUEUE_DIR)
                elif subq == 'owner':
                    msgdata.update({
                        'toowner'   : True,
                        'envsender' : config.SITE_OWNER_ADDRESS,
                        'pipeline'  : config.OWNER_PIPELINE,
                        })
                    queue = Switchboard(config.INQUEUE_DIR)
                elif subq is None:
                    msgdata['tolist'] = True
                    queue = Switchboard(config.INQUEUE_DIR)
                elif subq == 'request':
                     msgdata['torequest'] = True
                     queue = Switchboard(config.CMDQUEUE_DIR)
                else:
                    elog.error('Unknown sub-queue: %s', subq)
                    status.append(ERR_550)
                    continue
                queue.enqueue(msg, msgdata)
                status.append('250 Ok')
            except Exception, e:
                elog.error('%s', e)
                status.append(ERR_550)
        # All done; returning this big status string should give the expected
        # response to the LMTP client.
        return CRLF.join(status)

    def _cleanup(self):
        pass


server = LMTPRunner()
qlog.info('LMTPRunner qrunner started.')
asyncore.loop()
# We'll never get here, but just in case...
qlog.info('LMTPRunner qrunner exiting.')
