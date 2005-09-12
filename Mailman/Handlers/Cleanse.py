# Copyright (C) 1998-2005 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Cleanse certain headers from all messages."""

from email.Utils import formataddr

from Mailman.Logging.Syslog import syslog
from Mailman.Handlers.CookHeaders import uheader


def process(mlist, msg, msgdata):
    # Always remove this header from any outgoing messages.  Be sure to do
    # this after the information on the header is actually used, but before a
    # permanent record of the header is saved.
    del msg['approved']
    # Also remove this header since it can contain a password
    del msg['urgent']
    # We remove other headers from anonymous lists
    if mlist.anonymous_list:
        syslog('post', 'post to %s from %s anonymized',
               mlist.internal_name(), msg.get('from'))
        del msg['from']
        del msg['reply-to']
        del msg['sender']
        # Hotmail sets this one
        del msg['x-originating-email']
        i18ndesc = str(uheader(mlist, mlist.description, 'From'))
        msg['From'] = formataddr((i18ndesc, mlist.GetListEmail()))
        msg['Reply-To'] = mlist.GetListEmail()
    # Some headers can be used to fish for membership
    del msg['return-receipt-to']
    del msg['disposition-notification-to']
    del msg['x-confirm-reading-to']
    # Pegasus mail uses this one... sigh
    del msg['x-pmrqc']
    # Remove any "DomainKeys" (or similar) header lines.  The values contained
    # in these header lines are intended to be used by the recipient to detect
    # forgery or tampering in transit, and the modifications made by Mailman
    # to the headers and body of the message will cause these keys to appear
    # invalid.  Removing them will at least avoid this misleading result, and
    # it will also give the MTA the opportunity to regenerate valid keys
    # originating at the Mailman server for the outgoing message.
    del msg['domainkey-signature']
    del msg['dkim-signature']
