# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""The implicit destination rule."""

__all__ = ['ImplicitDestination']
__metaclass__ = type


import re
from email.utils import getaddresses
from zope.interface import implements

from mailman.i18n import _
from mailman.interfaces import IRule



class ImplicitDestination:
    """The implicit destination rule."""
    implements(IRule)

    name = 'implicit-dest'
    description = _('Catch messages with implicit destination.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        # Implicit destination checking must be enabled in the mailing list.
        if not mlist.require_explicit_destination:
            return False
        # Messages gated from NNTP will always have an implicit destination so
        # are never checked.
        if msgdata.get('fromusenet'):
            return False
        # Calculate the list of acceptable aliases.  If the alias starts with
        # a caret (i.e. ^), then it's a regular expression to match against.
        aliases = set()
        alias_patterns = set()
        for alias in mlist.acceptable_aliases.splitlines():
            alias = alias.strip().lower()
            if alias.startswith('^'):
                alias_patterns.add(alias)
            elif '@' in alias:
                aliases.add(alias)
            else:
                # This is not a regular expression, nor a fully-qualified
                # email address, so skip it.
                pass
        # Add the list's posting address, i.e. the explicit address, to the
        # set of acceptable aliases.
        aliases.add(mlist.posting_address)
        # Look at all the recipients.  If the recipient is any acceptable
        # alias (or the explicit posting address), then this rule does not
        # match.  If not, then add it to the set of recipients we'll check
        # against the alias patterns later.
        recipients = set()
        for header in ('to', 'cc', 'resent-to', 'resent-cc'):
            for fullname, address in getaddresses(msg.get_all(header, [])):
                address = address.lower()
                if address in aliases:
                    return False
                recipients.add(address)
        # Now for all alias patterns, see if any of the recipients matches a
        # pattern.  If so, then this rule does not match.
        for pattern in alias_patterns:
            escaped = re.escape(pattern)
            for recipient in recipients:
                try:
                    if re.match(pattern, recipient, re.IGNORECASE):
                        return False
                except re.error:
                    # The pattern is a malformed regular expression.  Try
                    # matching again with the pattern escaped.
                    try:
                        if re.match(escaped, recipient, re.IGNORECASE):
                            return False
                    except re.error:
                        pass
        # Nothing matched.
        return True
