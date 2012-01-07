# Copyright (C) 2000-2012 by the Free Software Foundation, Inc.
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

"""NNTP runner."""

import re
import email
import socket
import logging
import nntplib

from cStringIO import StringIO
from lazr.config import as_host_port

from mailman.config import config
from mailman.core.runner import Runner
from mailman.interfaces.nntp import NewsModeration

COMMASPACE = ', '
log = logging.getLogger('mailman.error')


# Matches our Mailman crafted Message-IDs.  See Utils.unique_message_id()
# XXX The move to email.utils.make_msgid() breaks this.
mcre = re.compile(r"""
    <mailman.                                     # match the prefix
    \d+.                                          # serial number
    \d+.                                          # time in seconds since epoch
    \d+.                                          # pid
    (?P<listname>[^@]+)                           # list's internal_name()
    @                                             # localpart@dom.ain
    (?P<hostname>[^>]+)                           # list's mail_host
    >                                             # trailer
    """, re.VERBOSE)



class NewsRunner(Runner):
    def _dispose(self, mlist, msg, msgdata):
        # Make sure we have the most up-to-date state
        mlist.Load()
        if not msgdata.get('prepped'):
            prepare_message(mlist, msg, msgdata)
        try:
            # Flatten the message object, sticking it in a StringIO object
            fp = StringIO(msg.as_string())
            conn = None
            try:
                try:
                    nntp_host, nntp_port = as_host_port(
                        mlist.nntp_host, default_port=119)
                    conn = nntplib.NNTP(nntp_host, nntp_port,
                                        readermode=True,
                                        user=config.nntp.username,
                                        password=config.nntp.password)
                    conn.post(fp)
                except nntplib.error_temp, e:
                    log.error('(NNTPDirect) NNTP error for list "%s": %s',
                              mlist.internal_name(), e)
                except socket.error, e:
                    log.error('(NNTPDirect) socket error for list "%s": %s',
                              mlist.internal_name(), e)
            finally:
                if conn:
                    conn.quit()
        except Exception, e:
            # Some other exception occurred, which we definitely did not
            # expect, so set this message up for requeuing.
            self._log(e)
            return True
        return False



def prepare_message(mlist, msg, msgdata):
    # If the newsgroup is moderated, we need to add this header for the Usenet
    # software to accept the posting, and not forward it on to the n.g.'s
    # moderation address.  The posting would not have gotten here if it hadn't
    # already been approved.  1 == open list, mod n.g., 2 == moderated
    if mlist.news_moderation in (NewsModeration.open_moderated,
                                 NewsModeration.moderated):
        del msg['approved']
        msg['Approved'] = mlist.posting_address
    # Should we restore the original, non-prefixed subject for gatewayed
    # messages? TK: We use stripped_subject (prefix stripped) which was
    # crafted in CookHeaders.py to ensure prefix was stripped from the subject
    # came from mailing list user.
    stripped_subject = msgdata.get('stripped_subject') \
                       or msgdata.get('origsubj')
    if not mlist.news_prefix_subject_too and stripped_subject is not None:
        del msg['subject']
        msg['subject'] = stripped_subject
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
            msg['Newsgroups'] = COMMASPACE.join(ngroups)
    else:
        # Newsgroups: isn't in the message
        msg['Newsgroups'] = mlist.linked_newsgroup
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
    hackmsgid = True
    if msgid:
        mo = mcre.search(msgid)
        if mo:
            lname, hname = mo.group('listname', 'hostname')
            if lname == mlist.internal_name() and hname == mlist.mail_host:
                hackmsgid = False
    if hackmsgid:
        del msg['message-id']
        msg['Message-ID'] = email.utils.make_msgid()
    # Lines: is useful
    if msg['Lines'] is None:
        # BAW: is there a better way?
        count = len(list(email.Iterators.body_line_iterator(msg)))
        msg['Lines'] = str(count)
    # Massage the message headers by remove some and rewriting others.  This
    # woon't completely sanitize the message, but it will eliminate the bulk
    # of the rejections based on message headers.  The NNTP server may still
    # reject the message because of other problems.
    for header in config.nntp.remove_headers.split():
        del msg[header]
    for rewrite_pairs in config.nntp.rewrite_duplicate_headers.splitlines():
        if len(rewrite_pairs.strip()) == 0:
            continue
        header, rewrite = rewrite_pairs.split()
        values = msg.get_all(header, [])
        if len(values) < 2:
            # We only care about duplicates
            continue
        del msg[header]
        # But keep the first one...
        msg[header] = values[0]
        for v in values[1:]:
            msg[rewrite] = v
    # Mark this message as prepared in case it has to be requeued
    msgdata['prepped'] = True
