# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""Utility for generating all the aliases of a mailing list."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MailTransportAgentAliases',
    ]


from zope.interface import implements

from mailman.interfaces.mta import IMailTransportAgentAliases


SUBDESTINATIONS = (
    'bounces',
    'confirm',
    'join',
    'leave',
    'owner',
    'request',
    'subscribe',
    'unsubscribe',
    )



class MailTransportAgentAliases:
    """Utility for generating all the aliases of a mailing list."""

    implements(IMailTransportAgentAliases)

    def aliases(self, mlist):
        """See `IMailTransportAgentAliases`."""
        # Always return
        yield mlist.posting_address
        for destination in sorted(SUBDESTINATIONS):
            yield '{0}-{1}@{2}'.format(
                mlist.list_name, destination, mlist.mail_host)

    def destinations(self, mlist):
        """See `IMailTransportAgentAliases`."""
        # Always return
        yield mlist.list_name
        for destination in sorted(SUBDESTINATIONS):
            yield '{0}-{1}'.format(mlist.list_name, destination)
