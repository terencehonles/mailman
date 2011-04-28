# Copyright (C) 2002-2011 by the Free Software Foundation, Inc.
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

"""sina.com bounces"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Sina',
    ]


import re

from email.iterators import body_line_iterator
from zope.interface import implements

from mailman.interfaces.bounce import IBounceDetector


acre = re.compile(r'<(?P<addr>[^>]*)>')



class Sina:
    """sina.com bounces"""

    implements(IBounceDetector)

    def process(self, msg):
        """See `IBounceDetector`."""
        if msg.get('from', '').lower() != 'mailer-daemon@sina.com':
            return set()
        if not msg.is_multipart():
            return set()
        # The interesting bits are in the first text/plain multipart.
        part = None
        try:
            part = msg.get_payload(0)
        except IndexError:
            pass
        if not part:
            return set()
        addresses = set()
        for line in body_line_iterator(part):
            mo = acre.match(line)
            if mo:
                addresses.add(mo.group('addr'))
        return addresses
