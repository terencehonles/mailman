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

"""Recognizes (some) Microsoft Exchange formats."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Exchange',
    ]


import re

from email.iterators import body_line_iterator
from zope.interface import implements

from mailman.interfaces.bounce import IBounceDetector


scre = re.compile('did not reach the following recipient')
ecre = re.compile('MSEXCH:')
a1cre = re.compile('SMTP=(?P<addr>[^;]+); on ')
a2cre = re.compile('(?P<addr>[^ ]+) on ')



class Exchange:
    """Recognizes (some) Microsoft Exchange formats."""

    implements(IBounceDetector)

    def process(self, msg):
        """See `IBounceDetector`."""
        addresses = set()
        it = body_line_iterator(msg)
        # Find the start line.
        for line in it:
            if scre.search(line):
                break
        else:
            return set()
        # Search each line until we hit the end line.
        for line in it:
            if ecre.search(line):
                break
            mo = a1cre.search(line)
            if not mo:
                mo = a2cre.search(line)
            if mo:
                addresses.add(mo.group('addr'))
        return set(addresses)
