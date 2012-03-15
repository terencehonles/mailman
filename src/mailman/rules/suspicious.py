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

"""The historical 'suspicious header' rule."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'SuspiciousHeader',
    ]


import re
import logging

from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.rules import IRule

log = logging.getLogger('mailman.error')



class SuspiciousHeader:
    """The historical 'suspicious header' rule."""
    implements(IRule)

    name = 'suspicious-header'
    description = _('Catch messages with suspicious headers.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        return (mlist.bounce_matching_headers and
                has_matching_bounce_header(mlist, msg))



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
                      mlist.display_name, line)
        else:
            header = line[:i]
            value = line[i+1:].lstrip()
            try:
                cre = re.compile(value, re.IGNORECASE)
            except re.error as error:
                # The regexp was malformed.  BAW: should do a better
                # job of informing the list admin.
                log.error("""\
bad regexp in bounce_matching_header line: %s
\n%s (cause: %s)""", mlist.display_name, value, error)
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
