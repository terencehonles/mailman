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

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'NNTPRunner',
    ]


import re
import email
import socket
import logging
import nntplib

from cStringIO import StringIO

from mailman.config import config
from mailman.core.runner import Runner
from mailman.interfaces.nntp import NewsModeration

COMMA = ','
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



class NNTPRunner(Runner):
    def _dispose(self, mlist, msg, msgdata):
        # Get NNTP server connection information.
        host = config.nntp.host.strip()
        port = config.nntp.port.strip()
        if len(port) == 0:
            port = 119
        else:
            try:
                port = int(port)
            except (TypeError, ValueError):
                log.exception('Bad [nntp]port value: {0}'.format(port))
                port = 119
        # Make sure we have the most up-to-date state
        if not msgdata.get('prepped'):
            prepare_message(mlist, msg, msgdata)
        # Flatten the message object, sticking it in a StringIO object
        fp = StringIO(msg.as_string())
        conn = None
        try:
            conn = nntplib.NNTP(host, port,
                                readermode=True,
                                user=config.nntp.user,
                                password=config.nntp.password)
            conn.post(fp)
        except nntplib.error_temp:
            log.exception('{0} NNTP error for {1}'.format(
                msg.get('message-id', 'n/a'), mlist.fqdn_listname))
        except socket.error:
            log.exception('{0} NNTP socket error for {1}'.format(
                msg.get('message-id', 'n/a'), mlist.fqdn_listname))
        except Exception:
            # Some other exception occurred, which we definitely did not
            # expect, so set this message up for requeuing.
            log.exception('{0} NNTP unexpected exception for {1}'.format(
                msg.get('message-id', 'n/a'), mlist.fqdn_listname))
            return True
        finally:
            if conn:
                conn.quit()
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
    stripped_subject = msgdata.get('stripped_subject',
                                   msgdata.get('original_subject'))
    # XXX 2012-03-31 BAW: rename news_prefix_subject_too to nntp_.  This
    # requires a schema change.
    if not mlist.news_prefix_subject_too and stripped_subject is not None:
        del msg['subject']
        msg['subject'] = stripped_subject
    # Add the appropriate Newsgroups header.  Multiple Newsgroups headers are
    # generally not allowed so we're not testing for them.
    header = msg.get('newsgroups')
    if header is None:
        msg['Newsgroups'] = mlist.linked_newsgroup
    else:
        # See if the Newsgroups: header already contains our linked_newsgroup.
        # If so, don't add it again.  If not, append our linked_newsgroup to
        # the end of the header list
        newsgroups = [value.strip() for value in header.split(COMMA)]
        if mlist.linked_newsgroup not in newsgroups:
            newsgroups.append(mlist.linked_newsgroup)
            # Subtitute our new header for the old one.
            del msg['newsgroups']
            msg['Newsgroups'] = COMMASPACE.join(newsgroups)
    # Note: We need to be sure two messages aren't ever sent to the same list
    # in the same process, since message ids need to be unique.  Further, if
    # messages are crossposted to two gated mailing lists, they must each have
    # unique message ids or the nntpd will only accept one of them.  The
    # solution here is to substitute any existing message-id that isn't ours
    # with one of ours, so we need to parse it to be sure we're not looping.
    #
    # Our Message-ID format is <mailman.secs.pid.listname@hostname>
    #
    # XXX 2012-03-31 BAW: What we really want to do is try posting the message
    # to the nntpd first, and only if that fails substitute a unique
    # Message-ID.  The following should get moved out of prepare_message() and
    # into _dispose() above.
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
    # Lines: is useful.
    if msg['Lines'] is None:
        # BAW: is there a better way?
        count = len(list(email.iterators.body_line_iterator(msg)))
        msg['Lines'] = str(count)
    # Massage the message headers by remove some and rewriting others.  This
    # won't completely sanitize the message, but it will eliminate the bulk of
    # the rejections based on message headers.  The NNTP server may still
    # reject the message because of other problems.
    for header in config.nntp.remove_headers.split():
        del msg[header]
    dup_headers = config.nntp.rewrite_duplicate_headers.split()
    if len(dup_headers) % 2 != 0:
        # There are an odd number of headers; ignore the last one.
        bad_header = dup_headers.pop()
        log.error('Ignoring odd [nntp]rewrite_duplicate_headers: {0}'.format(
            bad_header))
    dup_headers.reverse()
    while dup_headers:
        source = dup_headers.pop()
        target = dup_headers.pop()
        values = msg.get_all(source, [])
        if len(values) < 2:
            # We only care about duplicates.
            continue
        # Delete all the original headers.
        del msg[source]
        # Put the first value back on the original header.
        msg[source] = values[0]
        # And put all the subsequent values on the destination header.
        for value in values[1:]:
            msg[target] = value
    # Mark this message as prepared in case it has to be requeued.
    msgdata['prepped'] = True
