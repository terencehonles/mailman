# Copyright (C) 2006 by the Free Software Foundation, Inc.
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

FIXME

Most MTAs can be configured to deliver messages to a `LMTP'[1].  This
module is actually a server rather than a runner which picks up
files from queue directory and process as required.  LMTP runner opens
a local TCP port and waits for MTA to connect to it and receives messages.
The messages are subsequently injected into Mailman's qfiles for processing
in the normal pipeline.

All the incoming messages should be checked by MTA if they have valid
destination; messages which have invalid destination like non-existent
listname are discarded and recorded only in error log.

[1] RFC2033

See the variable USE_LMTP in Defaults.py.in for enabling this delivery
mechanism.
"""

# NOTE: LMTP delivery is experimental in Mailman 2.2.

import os
import smtpd
import logging
import asyncore
from cStringIO import StringIO

from email.Parser import Parser
from email.Utils import parseaddr

from Mailman import Utils
from Mailman.Message import Message
from Mailman.Queue.Runner import Runner
from Mailman.Queue.sbcache import get_switchboard
from Mailman.configuration import config

log = logging.getLogger('mailman.error')

# We only care about the listname and the subq as in listname@ or
# listname-request@
subqnames = ('admin','bounces','confirm','join','leave',
             'owner','request','subscribe','unsubscribe')

def getlistq(address):
    localpart, domain = address.split('@', 1)
    l = localpart.split('-')
    if l[-1] in subqnames:
        listname = '-'.join(l[:-1])
        subq = l[-1]
    else:
        listname = localpart
        subq = None
    return listname, subq, domain


class SMTPChannel(smtpd.SMTPChannel):
    # Override smtpd.SMTPChannel but can't change the class name.
    # LMTP greeting is LHLO and no HELO/EHLO

    def smtp_LHLO(self, arg):
        smtpd.SMTPChannel.smtp_HELO(self, arg)

    def smtp_HELO(self, arg):
        self.push('502 Error: command HELO not implemented')


class LMTPRunner(Runner, smtpd.SMTPServer):
    # Only __init__ is called on startup. Asyncore is responsible for
    # later connections from MTA.

    def __init__(self, slice=None, numslices=1, 
                 localaddr=(config.LMTP_HOST, config.LMTP_PORT),
		 remoteaddr=None):
        self._stop = 0
        self._parser = Parser(Message)
	smtpd.SMTPServer.__init__(self, localaddr, remoteaddr)

    def handle_accept(self):
        conn, addr = self.accept()
	channel = SMTPChannel(self, conn, addr)

    def process_message(self, peer, mailfrom, rcpttos, data):
        # Refresh this each time through the list.
        listnames = Utils.list_names()
	fp = StringIO(data)
	for to in rcpttos:
	    try:
	        to = parseaddr(to)[1].lower()
		listname, subq, domain = getlistq(to)
		listname = listname + '@' + domain
		if listname not in listnames:
                    raise Mailman.Errors.MMUnknownListError, listname
		fp.seek(0)
		msg = self._parser.parse(fp)
		msg['X-MailFrom'] = mailfrom
		msgdata = {'listname': listname}
		if subq in ('bounces', 'admin'):
		    queue = get_switchboard(config.BOUNCEQUEUE_DIR)
	        elif subq == 'confirm':
                    msgdata['toconfirm'] = 1
                    queue = get_switchboard(config.CMDQUEUE_DIR)
                elif subq in ('join', 'subscribe'):
                    msgdata['tojoin'] = 1
                    queue = get_switchboard(config.CMDQUEUE_DIR)
                elif subq in ('leave', 'unsubscribe'):
                    msgdata['toleave'] = 1
                    queue = get_switchboard(config.CMDQUEUE_DIR)
                elif subq == 'owner':
                    msgdata.update({
                        'toowner': True,
                        'envsender': config.SITE_OWNER_ADDRESS,
                        'pipeline': config.OWNER_PIPELINE,
                        })
                    queue = get_switchboard(config.INQUEUE_DIR)
                elif subq is None:
                    msgdata['tolist'] = 1
		    queue = get_switchboard(config.INQUEUE_DIR)
                elif subq == 'request':
		     msgdata['torequest'] = 1
		     queue = get_switchboard(config.CMDQUEUE_DIR)
		else:
                    log.error('Unknown sub-queue: %s', subq)
                    continue
                queue.enqueue(msg, msgdata)
            except Exception, e:
                log.error('%s', e)

    def _cleanup(self):
        pass


server = LMTPRunner()
asyncore.loop()

