# Copyright (C) 1998-2011 by the Free Software Foundation, Inc.
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

"""Microsoft's `SMTPSVC' nears I kin tell."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Microsoft',
    ]


import re

from cStringIO import StringIO
from flufl.enum import Enum
from zope.interface import implements

from mailman.interfaces.bounce import IBounceDetector


scre = re.compile(r'transcript of session follows', re.IGNORECASE)


class ParseState(Enum):
    start = 0
    tag_seen = 1



class Microsoft:
    """Microsoft's `SMTPSVC' nears I kin tell."""

    implements(IBounceDetector)

    def process(self, msg):
        if msg.get_content_type() != 'multipart/mixed':
            return set()
        # Find the first subpart, which has no MIME type.
        try:
            subpart = msg.get_payload(0)
        except IndexError:
            # The message *looked* like a multipart but wasn't.
            return set()
        data = subpart.get_payload()
        if isinstance(data, list):
            # The message is a multi-multipart, so not a matching bounce.
            return set()
        body = StringIO(data)
        state = ParseState.start
        addresses = set()
        for line in body:
            if state is ParseState.start:
                if scre.search(line):
                    state = ParseState.tag_seen
            elif state is ParseState.tag_seen:
                if '@' in line:
                    addresses.add(line.strip())
        return set(addresses)
