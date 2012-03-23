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

"""RFC 2369 List-* and related headers."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'RFC2369',
    ]


from email.utils import formataddr
from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.handlers.cook_headers import uheader
from mailman.interfaces.handler import IHandler


CONTINUATION = ',\n\t'



def process(mlist, msg, msgdata):
    """Add the RFC 2369 List-* and related headers."""
    # Some people really hate the List-* headers.  It seems that the free
    # version of Eudora (possibly on for some platforms) does not hide these
    # headers by default, pissing off their users.  Too bad.  Fix the MUAs.
    if not mlist.include_rfc2369_headers:
        return
    list_id = '{0.list_name}.{0.mail_host}'.format(mlist)
    if mlist.description:
        # Don't wrap the header since here we just want to get it properly RFC
        # 2047 encoded.
        i18ndesc = uheader(mlist, mlist.description, 'List-Id', maxlinelen=998)
        listid_h = formataddr((str(i18ndesc), list_id))
    else:
        # Without a description, we need to ensure the MUST brackets.
        listid_h = '<{0}>'.format(list_id)
    # No other agent should add a List-ID header except Mailman.
    del msg['list-id']
    msg['List-Id'] = listid_h
    # For internally crafted messages, we also add a (nonstandard),
    # "X-List-Administrivia: yes" header.  For all others (i.e. those coming
    # from list posts), we add a bunch of other RFC 2369 headers.
    requestaddr = mlist.request_address
    subfieldfmt = '<{0}>, <mailto:{1}>'
    listinfo = mlist.script_url('listinfo')
    headers = {}
    # XXX reduced_list_headers used to suppress List-Help, List-Subject, and
    # List-Unsubscribe from UserNotification.  That doesn't seem to make sense
    # any more, so always add those three headers (others will still be
    # suppressed).
    headers.update({
        'List-Help'       : '<mailto:{0}?subject=help>'.format(requestaddr),
        'List-Unsubscribe': subfieldfmt.format(listinfo, mlist.leave_address),
        'List-Subscribe'  : subfieldfmt.format(listinfo, mlist.join_address),
        })
    if not msgdata.get('reduced_list_headers'):
        # List-Post: is controlled by a separate attribute
        if mlist.include_list_post_header:
            headers['List-Post'] = '<mailto:{0}>'.format(mlist.posting_address)
        # Add RFC 2369 and 5064 archiving headers, if archiving is enabled.
        if mlist.archive:
            for archiver in config.archivers:
                headers['List-Archive'] = '<{0}>'.format(
                    archiver.list_url(mlist))
                permalink = archiver.permalink(mlist, msg)
                if permalink is not None:
                    headers['Archived-At'] = permalink
    # XXX RFC 2369 also defines a List-Owner header which we are not currently
    # supporting, but should.
    for h, v in headers.items():
        # First we delete any pre-existing headers because the RFC permits
        # only one copy of each, and we want to be sure it's ours.
        del msg[h]
        # Wrap these lines if they are too long.  78 character width probably
        # shouldn't be hardcoded, but is at least text-MUA friendly.  The
        # adding of 2 is for the colon-space separator.
        if len(h) + 2 + len(v) > 78:
            v = CONTINUATION.join(v.split(', '))
        msg[h] = v



class RFC2369:
    """Add the RFC 2369 List-* headers."""

    implements(IHandler)

    name = 'rfc-2369'
    description = _('Add the RFC 2369 List-* headers.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        process(mlist, msg, msgdata)
