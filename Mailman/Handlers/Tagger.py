# Copyright (C) 2001 by the Free Software Foundation, Inc.
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

"""Extract topics from the original mail message.
"""

import re
import email
import email.Iterators

from Mailman.Logging.Syslog import syslog

CRNL = '\r\n'
NL = '\n'
NLTAB = '\n\t'



def process(mlist, msg, msgdata):
    if not mlist.topics:
        return
    # Extract the Subject:, Keywords:, and possibly body text
    matchlines = []
    matchlines.append(msg.get('subject', None))
    matchlines.append(msg.get('keywords', None))
    if mlist.topics_bodylines_limit == 0:
        # Don't scan any body lines
        pass
    elif mlist.topics_bodylines_limit < 0:
        # Scan all body lines
        matchlines.extend(scanbody(msg))
    else:
        # Scan just some of the body lines
        matchlines.extend(scanbody(msg, mlist.topics_bodylines_limit))
    matchlines = filter(None, matchlines)
    # For each regular expression in the topics list, see if any of the lines
    # of interest from the message match the regexp.  If so, the message gets
    # added to the specific topics bucket.
    hits = {}
    for name, pattern, desc, emptyflag in mlist.topics:
        cre = re.compile(pattern, re.IGNORECASE | re.VERBOSE)
        for line in matchlines:
            if cre.search(line):
                hits[name] = 1
                break
    if hits:
        msgdata['topichits'] = hits.keys()
        msg['X-Topics'] = NLTAB.join(hits.keys())
    


def scanbody(msg, numlines=None):
    # We only scan the body of the message if it is of MIME type text/plain,
    # or if the outer type is multipart/alternative and there is a text/plain
    # part.  Anything else, and the body is ignored for header-scan purposes.
    found = None
    if msg.gettype('text/plain') == 'text/plain':
        found = msg
    elif msg.ismultipart() and msg.gettype() == 'multipart/alternative':
        for found in msg.get_payload():
            if found.gettype('text/plain') == 'text/plain':
                break
        else:
            found = None
    if not found:
        return []
    # Now that we have a Message object that meets our criteria, let's extract
    # the first numlines of body text.
    lines = []
    lineno = 0
    reader = email.Iterators.body_line_iterator(msg)
    while numlines is None or lineno < numlines:
        try:
            line = reader.pop(0)
        except IndexError:
            break
        # Blank lines don't count
        if not line.strip():
            continue
        lineno += 1
        # Stop scanning if we find a line that would not be recognized as
        # either a header or a continuation line
        if line[0] not in ' \t' and line.find(':') < 0:
            break
        lines.append(line)
    # Concatenate those body text lines with newlines, and then create a new
    # message object from those lines.
    msg = email.message_from_string(NL.join(lines))
    return msg.getall('subject', []) + msg.getall('keywords', [])
