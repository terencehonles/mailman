# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

"""Application level bounce handling."""

__all__ = [
    'bounce_message',
    'has_matching_bounce_header',
    ]

import re
import logging

from email.mime.message import MIMEMessage
from email.mime.text import MIMEText
from email.utils import getaddresses

from Mailman import Message
from Mailman import Utils
from Mailman.i18n import _

log = logging.getLogger('mailman.config')



def bounce_message(mlist, msg, e=None):
    # Bounce a message back to the sender, with an error message if provided
    # in the exception argument.
    sender = msg.get_sender()
    subject = msg.get('subject', _('(no subject)'))
    subject = Utils.oneline(subject,
                            Utils.GetCharSet(mlist.preferred_language))
    if e is None:
        notice = _('[No bounce details are available]')
    else:
        notice = _(e.notice)
    # Currently we always craft bounces as MIME messages.
    bmsg = Message.UserNotification(msg.get_sender(),
                                    mlist.owner_address,
                                    subject,
                                    lang=mlist.preferred_language)
    # BAW: Be sure you set the type before trying to attach, or you'll get
    # a MultipartConversionError.
    bmsg.set_type('multipart/mixed')
    txt = MIMEText(notice,
                   _charset=Utils.GetCharSet(mlist.preferred_language))
    bmsg.attach(txt)
    bmsg.attach(MIMEMessage(msg))
    bmsg.send(mlist)



def _parse_matching_header_opt(mlist):
    """Return a list of triples [(field name, regex, line), ...]."""
    # - Blank lines and lines with '#' as first char are skipped.
    # - Leading whitespace in the matchexp is trimmed - you can defeat
    #   that by, eg, containing it in gratuitous square brackets.
    all = []
    for line in mlist.bounce_matching_headers.splitlines():
        line = line.strip()
        # Skip blank lines and lines *starting* with a '#'.
        if not line or line.startswith('#'):
            continue
        i = line.find(':')
        if i < 0:
            # This didn't look like a header line.  BAW: should do a
            # better job of informing the list admin.
            log.error('bad bounce_matching_header line: %s\n%s',
                      mlist.real_name, line)
        else:
            header = line[:i]
            value = line[i+1:].lstrip()
            try:
                cre = re.compile(value, re.IGNORECASE)
            except re.error, e:
                # The regexp was malformed.  BAW: should do a better
                # job of informing the list admin.
                log.error("""\
bad regexp in bounce_matching_header line: %s
\n%s (cause: %s)""", mlist.real_name, value, e)
            else:
                all.append((header, cre, line))
    return all


def has_matching_bounce_header(mlist, msg):
    """Does the message have a matching bounce header?

    :param mlist: The mailing list the message is destined for.
    :param msg: The email message object.
    :return: True if a header field matches a regexp in the
        bounce_matching_header mailing list variable.
    """
    for header, cre, line in _parse_matching_header_opt(mlist):
        for value in msg.get_all(header, []):
            if cre.search(value):
                return True
    return False
