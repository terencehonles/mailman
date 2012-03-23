# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

"""Cleanse certain headers from all messages."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Cleanse',
    ]


import logging

from email.utils import formataddr
from zope.interface import implements

from mailman.core.i18n import _
from mailman.handlers.cook_headers import uheader
from mailman.interfaces.handler import IHandler


log = logging.getLogger('mailman.post')



class Cleanse:
    """Cleanse certain headers from all messages."""

    implements(IHandler)

    name = 'cleanse'
    description = _('Cleanse certain headers from all messages.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        # Remove headers that could contain passwords.
        del msg['approved']
        del msg['approve']
        del msg['x-approved']
        del msg['x-approve']
        del msg['urgent']
        # We remove other headers from anonymous lists.
        if mlist.anonymous_list:
            log.info('post to %s from %s anonymized',
                     mlist.fqdn_listname, msg.get('from'))
            del msg['from']
            del msg['reply-to']
            del msg['sender']
            # Hotmail sets this one
            del msg['x-originating-email']
            i18ndesc = str(uheader(mlist, mlist.description, 'From'))
            msg['From'] = formataddr((i18ndesc, mlist.posting_address))
            msg['Reply-To'] = mlist.posting_address
        # Some headers can be used to fish for membership.
        del msg['return-receipt-to']
        del msg['disposition-notification-to']
        del msg['x-confirm-reading-to']
        # Pegasus mail uses this one... sigh.
        del msg['x-pmrqc']
        # Don't let this header be spoofed.  See RFC 5064.
        del msg['archived-at']
