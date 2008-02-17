# Copyright (C) 2006-2008 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Remove any 'DomainKeys' (or similar) headers.

The values contained in these header lines are intended to be used by the
recipient to detect forgery or tampering in transit, and the modifications
made by Mailman to the headers and body of the message will cause these keys
to appear invalid.  Removing them will at least avoid this misleading result,
and it will also give the MTA the opportunity to regenerate valid keys
originating at the Mailman server for the outgoing message.
"""

__metaclass__ = type
__all__ = ['CleanseDKIM']


from zope.interface import implements

from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.interfaces import IHandler



class CleanseDKIM:
    """Remove DomainKeys headers."""

    implements(IHandler)

    name = 'cleanse-dkim'
    description = _('Remove DomainKeys headers.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        if config.REMOVE_DKIM_HEADERS:
            del msg['domainkey-signature']
            del msg['dkim-signature']
            del msg['authentication-results']
