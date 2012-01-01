# Copyright (C) 2001-2012 by the Free Software Foundation, Inc.
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

"""Extract topics from the original mail message."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Tagger',
    ]


import re
import email.iterators
import email.parser

from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler


OR = '|'
CRNL = '\r\n'
EMPTYBYTES = b''
NLTAB = '\n\t'



def process(mlist, msg, msgdata):
    """Tag the message for topics."""
    if not mlist.topics_enabled:
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
    # Filter out any 'false' items.
    matchlines = [item for item in matchlines if item]
    # For each regular expression in the topics list, see if any of the lines
    # of interest from the message match the regexp.  If so, the message gets
    # added to the specific topics bucket.
    hits = {}
    for name, pattern, desc, emptyflag in mlist.topics:
        pattern = OR.join(pattern.splitlines())
        cre = re.compile(pattern, re.IGNORECASE)
        for line in matchlines:
            if cre.search(line):
                hits[name] = 1
                break
    if hits:
        # Sort the keys and make them available both in the message metadata
        # and in a message header.
        msgdata['topichits'] = sorted(hits)
        msg['X-Topics'] = NLTAB.join(sorted(hits))



def scanbody(msg, numlines=None):
    """Scan the body for keywords."""
    # We only scan the body of the message if it is of MIME type text/plain,
    # or if the outer type is multipart/alternative and there is a text/plain
    # part.  Anything else, and the body is ignored for header-scan purposes.
    found = None
    if msg.get_content_type() == 'text/plain':
        found = msg
    elif msg.is_multipart()\
         and msg.get_content_type() == 'multipart/alternative':
        for found in msg.get_payload():
            if found.get_content_type() == 'text/plain':
                break
        else:
            found = None
    if not found:
        return []
    # Now that we have a Message object that meets our criteria, let's extract
    # the first numlines of body text.
    lines = []
    lineno = 0
    reader = list(email.iterators.body_line_iterator(msg))
    while numlines is None or lineno < numlines:
        try:
            line = bytes(reader.pop(0))
        except IndexError:
            break
        # Blank lines don't count
        if not line.strip():
            continue
        lineno += 1
        lines.append(line)
    # Concatenate those body text lines with newlines, and then create a new
    # message object from those lines.
    p = _ForgivingParser()
    msg = p.parsestr(EMPTYBYTES.join(lines))
    return msg.get_all('subject', []) + msg.get_all('keywords', [])



class _ForgivingParser(email.parser.HeaderParser):
    """An lax email parser.

    Be a little more forgiving about non-header/continuation lines, since
    we'll just read as much as we can from 'header-like' lines in the body.
    """
    # BAW: WIBNI we didn't have to cut-n-paste this whole thing just to
    # specialize the way it returns?
    def _parseheaders(self, container, fp):
        """See `email.parser.HeaderParser`."""
        # Parse the headers, returning a list of header/value pairs.  None as
        # the header means the Unix-From header.
        lastheader = ''
        lastvalue = []
        lineno = 0
        while 1:
            # Don't strip the line before we test for the end condition,
            # because whitespace-only header lines are RFC compliant
            # continuation lines.
            line = fp.readline()
            if not line:
                break
            line = line.splitlines()[0]
            if not line:
                break
            # Ignore the trailing newline
            lineno += 1
            # Check for initial Unix From_ line
            if line.startswith('From '):
                if lineno == 1:
                    container.set_unixfrom(line)
                    continue
                else:
                    break
            # Header continuation line
            if line[0] in ' \t':
                if not lastheader:
                    break
                lastvalue.append(line)
                continue
            # Normal, non-continuation header.  BAW: this should check to make
            # sure it's a legal header, e.g. doesn't contain spaces.  Also, we
            # should expose the header matching algorithm in the API, and
            # allow for a non-strict parsing mode (that ignores the line
            # instead of raising the exception).
            i = line.find(':')
            if i < 0:
                break
            if lastheader:
                container[lastheader] = NLTAB.join(lastvalue)
            lastheader = line[:i]
            lastvalue = [line[i+1:].lstrip()]
        # Make sure we retain the last header
        if lastheader:
            container[lastheader] = NLTAB.join(lastvalue)



class Tagger:
    """Tag messages with topic matches."""

    implements(IHandler)

    name = 'tagger'
    description = _('Tag messages with topic matches.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        process(mlist, msg, msgdata)
