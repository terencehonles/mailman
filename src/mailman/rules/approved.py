# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""Look for moderator pre-approval."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Approved',
    ]


import re
from email.iterators import typed_subpart_iterator
from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.rules import IRule


EMPTYSTRING = ''
HEADERS = [
    'approve',
    'approved',
    'x-approve',
    'x-approved',
    ]



class Approved:
    """Look for moderator pre-approval."""
    implements(IRule)

    name = 'approved'
    description = _('The message has a matching Approve or Approved header.')
    record = True

    def _get_password(self, msg, missing):
        for header in HEADERS:
            password = msg.get(header, missing)
            if password is not missing:
                return password
        return missing

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        # See if the message has an Approved or Approve header with a valid
        # moderator password.  Also look at the first non-whitespace line in
        # the file to see if it looks like an Approved header.
        missing = object()
        password = self._get_password(msg, missing)
        if password is missing:
            # Find the first text/plain part in the message
            part = None
            stripped = False
            for part in typed_subpart_iterator(msg, 'text', 'plain'):
                break
            payload = part.get_payload(decode=True)
            if payload is not None:
                line = ''
                lines = payload.splitlines(True)
                for lineno, line in enumerate(lines):
                    if line.strip() <> '':
                        break
                if ':' in line:
                    header, value = line.split(':', 1)
                    if header.lower() in HEADERS:
                        password = value.strip()
                        # Now strip the first line from the payload so the
                        # password doesn't leak.
                        del lines[lineno]
                        reset_payload(part, EMPTYSTRING.join(lines))
                        stripped = True
            if stripped:
                # Now try all the text parts in case it's
                # multipart/alternative with the approved line in HTML or
                # other text part.  We make a pattern from the Approved line
                # and delete it from all text/* parts in which we find it.  It
                # would be better to just iterate forward, but email
                # compatability for pre Python 2.2 returns a list, not a true
                # iterator.
                #
                # This will process all the multipart/alternative parts in the
                # message as well as all other text parts.  We shouldn't find
                # the pattern outside the multipart/alternative parts, but if
                # we do, it is probably best to delete it anyway as it does
                # contain the password.
                #
                # Make a pattern to delete.  We can't just delete a line
                # because line of HTML or other fancy text may include
                # additional message text.  This pattern works with HTML.  It
                # may not work with rtf or whatever else is possible.
                pattern = header + ':(\s|&nbsp;)*' + re.escape(password)
                for part in typed_subpart_iterator(msg, 'text'):
                    payload = part.get_payload(decode=True)
                    if payload is not None:
                        if re.search(pattern, payload):
                            reset_payload(part, re.sub(pattern, '', payload))
        else:
            for header in HEADERS:
                del msg[header]
        return password is not missing and password == mlist.moderator_password



def reset_payload(part, payload):
    # Set decoded payload maintaining content-type, charset, format and delsp.
    charset = part.get_content_charset() or 'us-ascii'
    content_type = part.get_content_type()
    format = part.get_param('format')
    delsp = part.get_param('delsp')
    del part['content-transfer-encoding']
    del part['content-type']
    part.set_payload(payload, charset)
    part.set_type(content_type)
    if format:
        part.set_param('Format', format)
    if delsp:
        part.set_param('DelSp', delsp)
