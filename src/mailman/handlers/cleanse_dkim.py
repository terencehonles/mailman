# Copyright (C) 2006-2012 by the Free Software Foundation, Inc.
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

"""Remove any 'DomainKeys' (or similar) headers.

The values contained in these header lines are intended to be used by the
recipient to detect forgery or tampering in transit, and the modifications
made by Mailman to the headers and body of the message will cause these keys
to appear invalid.  Removing them will at least avoid this misleading result,
and it will also give the MTA the opportunity to regenerate valid keys
originating at the Mailman server for the outgoing message.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'CleanseDKIM',
    ]


from lazr.config import as_boolean
from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler



class CleanseDKIM:
    """Remove DomainKeys headers."""

    implements(IHandler)

    name = 'cleanse-dkim'
    description = _('Remove DomainKeys headers.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        if as_boolean(config.mta.remove_dkim_headers):
            del msg['domainkey-signature']
            del msg['dkim-signature']
            del msg['authentication-results']
