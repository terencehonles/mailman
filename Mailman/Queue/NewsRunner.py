# Copyright (C) 2000,2001 by the Free Software Foundation, Inc.
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

"""NNTP queue runner."""

import re
import socket
import nntplib

from mimelib.MsgReader import MsgReader
from mimelib.address import getaddresses

from Mailman import mm_cfg
from Mailman import Utils
from Mailman.Queue.Runner import Runner
from Mailman.Logging.Syslog import syslog
from Mailman.pythonlib.StringIO import StringIO

# Matches our Mailman crafted Message-IDs.  See Utils.unique_message_id()
mcre = re.compile(r"""
    <mailman.                                     # match the prefix
    \d+.                                          # serial number
    \d+.                                          # time in seconds since epoch
    \d+.                                          # pid
    (?P<listname>[^@]+)                           # list's internal_name()
    @                                             # localpart@dom.ain
    (?P<hostname>[^>]+)                           # list's host_name
    >                                             # trailer
    """, re.VERBOSE)



class NewsRunner(Runner):
    def __init__(self, slice=None, numslices=1, cachelists=1):
        Runner.__init__(self, mm_cfg.NEWSQUEUE_DIR,
                        slice, numslices, cachelists)

    def _dispose(self, mlist, msg, msgdata):
        if not msgdata.get('prepped'):
            prepare_message(mlist, msg, msgdata)
        try:
            # Flatten the message object, sticking it in a StringIO object
            fp = StringIO(str(msg))
            conn = None
            try:
                try:
                    conn = nntplib.NNTP(mlist.nntp_host, readermode=1,
                                        user=mm_cfg.NNTP_USERNAME,
                                        password=mm_cfg.NNTP_PASSWORD)
                    conn.post(fp)
                except nntplib.error_temp, e:
                    syslog('error',
                           '(NNTPDirect) NNTP error for list "%s": %s',
                           mlist.internal_name(), e)
                except socket.error, e:
                    syslog('error',
                           '(NNTPDirect) socket error for list "%s": %s',
                           mlist.internal_name(), e)
            finally:
                if conn:
                    conn.quit()
        except Exception, e:
            # Some other exception occurred, which we definitely did not
            # expect, so set this message up for requeuing.
            self._log(e)
            return 1
        return 0



def prepare_message(mlist, msg, msgdata):
    # Add the appropriate Newsgroups: header
    ngheader = msg['newsgroups']
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
    msgid = msg['message-id']
    hackmsgid = 1
    if msgid:
        mo = mcre.search(msgid)
        if mo:
            lname, hname = mo.group('listname', 'hostname')
            if lname == mlist.internal_name() and hname == mlist.host_name:
                hackmsgid = 0
    if hackmsgid:
        del msg['message-id']
        msg['Message-ID'] = Utils.unique_message_id(mlist)
    #
    # Lines: is useful
    if msg['Lines'] is None:
        # BAW: is there a better way?
        reader = MsgReader(msg)
        count = 0
        while 1:
            line = reader.readline()
            if not line:
                break
            count += 1
        msg['Lines'] = str(count)
    #
    # Get rid of these lines
    del msg['received']
    #
    # BAW: Gross hack to ensure that we have only one
    # content-transfer-encoding header.  More than one barfs NNTP.  I don't
    # know why we sometimes have more than one such header, and it probably
    # isn't correct to take the value of just the first one.  What if there
    # are conflicting headers???
    #
    # This relies on the fact that the legal values are usually not parseable
    # as addresses.  Yes this is another bogosity.
    cteheaders = getaddresses(msg.getall('content-transfer-encoding'))
    if cteheaders:
        ctetuple = cteheaders[0]
        ctevalue = ctetuple[1]
        del msg['content-transfer-encoding']
        msg['content-transfer-encoding'] = ctevalue
    # Mark this message as prepared in case it has to be requeued
    msgdata['prepped'] = 1
