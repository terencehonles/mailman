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

"""Yahoo! has its own weird format for bounces."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Yahoo',
    ]


import re
import email

from email.utils import parseaddr
from flufl.enum import Enum
from zope.interface import implements

from mailman.interfaces.bounce import IBounceDetector


tcre = re.compile(r'message\s+from\s+yahoo\.\S+', re.IGNORECASE)
acre = re.compile(r'<(?P<addr>[^>]*)>:')
ecre = re.compile(r'--- Original message follows')


class ParseState(Enum):
    start = 0
    tag_seen = 1



class Yahoo:
    """Yahoo! bounce detection."""

    implements(IBounceDetector)

    def process(self, msg):
        """See `IBounceDetector`."""
        # Yahoo! bounces seem to have a known subject value and something
        # called an x-uidl: header, the value of which seems unimportant.
        sender = parseaddr(msg.get('from', '').lower())[1] or ''
        if not sender.startswith('mailer-daemon@yahoo'):
            return set()
        addresses = set()
        state = ParseState.start
        for line in email.Iterators.body_line_iterator(msg):
            line = line.strip()
            if state is ParseState.start and tcre.match(line):
                state = ParseState.tag_seen
            elif state is ParseState.tag_seen:
                mo = acre.match(line)
                if mo:
                    addresses.add(mo.group('addr'))
                    continue
                mo = ecre.match(line)
                if mo:
                    # We're at the end of the error response.
                    break
        return addresses
