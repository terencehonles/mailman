# Copyright (C) 2001-2011 by the Free Software Foundation, Inc.
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

"""LLNL's custom Sendmail bounce message."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'LLNL',
    ]


import re

from email.iterators import body_line_iterator
from zope.interface import implements

from mailman.interfaces.bounce import IBounceDetector


acre = re.compile(r',\s*(?P<addr>\S+@[^,]+),', re.IGNORECASE)



class LLNL:
    """LLNL's custom Sendmail bounce message."""

    implements(IBounceDetector)

    def process(self, msg):
        """See `IBounceDetector`."""

        for line in body_line_iterator(msg):
            mo = acre.search(line)
            if mo:
                return set([mo.group('addr')])
        return set()
