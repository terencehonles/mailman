# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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

"""Move the message to the mail->news queue."""

import os
import time
import re

from Mailman import Message
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog

COMMASPACE = ', '



def process(mlist, msg, msgdata):
    # short circuits
    if not mlist.gateway_to_news or \
           msgdata.get('isdigest') or \
           msgdata.get('fromusenet'):
        return
    # sanity checks
    error = []
    if not mlist.linked_newsgroup:
        error.append('no newsgroup')
    if not mlist.nntp_host:
        error.append('no NNTP host')
    if error:
        syslog('error', 'NNTP gateway improperly configured: ' +
               COMMASPACE.join(error))
        return
    # Make a copy of the message to prepare for Usenet
    msg = Message.OutgoingMessage(repr(msg))
    # Add the appropriate Newsgroups: header
    ngheader = msg.getheader('newsgroups')
    if ngheader is not None:
        # See if the Newsgroups: header already contains our linked_newsgroup.
        # If so, don't add it again.  If not, append our linked_newsgroup to
        # the end of the header list
        ngroups = [s.strip() for s in ngheader.split(',')]
        if mlist.linked_newsgroup not in ngroups:
            ngroups.append(mlist.linked_newsgroup)
            # Subtitute our new header for the old one.
            del msg['newsgroups']
            msg['Newsgroups'] = COMMA.join(ngroups)
    else:
        # Newsgroups: isn't in the message
        msg['Newsgroups'] = mlist.linked_newsgroup
    #
    # Note: We need to be sure two messages aren't ever sent to the same list
    # in the same process, since message ids need to be unique.  Further, if
    # messages are crossposted to two Usenet-gated mailing lists, they each
    # need to have unique message ids or the nntpd will only accept one of
    # them.  The solution here is to substitute any existing message-id that
    # isn't ours with one of ours, so we need to parse it to be sure we're not
    # looping.
    #
    # Our Message-ID format is <mailman.secs.pid.listname@hostname>
    msgid = msg.get('message-id')
    hackmsgid = 1
    if msgid:
        mo = re.search(
            msgid,
            r'<mailman.\d+.\d+.(?P<listname>[^@]+)@(?P<hostname>[^>]+)>')
        if mo:
            lname, hname = mo.group('listname', 'hostname')
            if lname == mlist.internal_name() and hname == mlist.host_name:
                hackmsgid = 0
    if hackmsgid:
        del msg['message-id']
        msg['Message-ID'] = '<mailman.%d.%d.%s@%s>' % (
            time.time(), os.getpid(), mlist.internal_name(), mlist.host_name)
    #
    # Lines: is useful
    if msg.getheader('lines') is None:
        msg['Lines'] = str(msg.body.count('\n') + 1)
    #
    # Get rid of these lines
    del msg['received']
    #
    # TBD: Gross hack to ensure that we have only one
    # content-transfer-encoding header.  More than one barfs NNTP.  I don't
    # know why we sometimes have more than one such header, and it probably
    # isn't correct to take the value of just the first one.  What if there
    # are conflicting headers???
    #
    # This relies on the new interface for getaddrlist() returning values for
    # all present headers, and the fact that the legal values are usually not
    # parseable as addresses.  Yes this is another bogosity.
    cteheaders = msg.getaddrlist('content-transfer-encoding')
    if cteheaders:
        ctetuple = cteheaders[0]
        ctevalue = ctetuple[1]
        del msg['content-transfer-encoding']
        msg['content-transfer-encoding'] = ctevalue
    # NNTP is strict about spaces after the colon in headers.
    for n in range(len(msg.headers)):
        line = msg.headers[n]
        i = line.find(':')
        if i <> -1 and line[i+1] <> ' ':
            msg.headers[n] = line[:i+1] + ' ' + line[i+1:]
    #
    # Write the message into the outgoing NNTP queue.
    msg.Requeue(mlist, newdata=msgdata,
                _whichq = mm_cfg.NEWSQUEUE_DIR)
