# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Parse RFC 1894 (i.e. DSN) bounce formats."""

from mimelib import address
from Mailman.pythonlib.StringIO import StringIO



def parseaddr(val):
    try:
        atype, addr = val.split(';', 1)
    except ValueError:
        # Bogus format for Original-Recipient: or Final-Recipient:
        return None
    if atype.lower() <> 'rfc822':
        # Don't know what to do with this address type
        return None
    addr = addr.strip()
    if not addr:
        return None
    return address.unquote(addr)



def check(msg):
    if msg.ismultipart():
        # Recursively check the subparts
        for subpart in msg.get_payload():
            addrs = check(subpart)
            if addrs:
                return addrs
        return None
    # It's not a multipart/* object, so see if it's got the content-type
    # specified in the DSN spec.
    if msg.gettype() <> 'message/delivery-status':
        # This content-type doesn't help us
        return None
    # BAW: could there be more than one DSN per message?
    #
    # Now parse out the per-recipient fields, which are separated by blank
    # lines.  The first block is actually the per-notification fields, but
    # those can be safely ignored
    #
    # We try to dig out the Original-Recipient (which is optional) and
    # Final-Recipient (which is mandatory, but may not exactly match an
    # address on our list).  Some MTA's also use X-Actual-Recipeint as a
    # synonym for Original-Recipeint, but some apparently use that for
    # other purposes :(
    #
    # Also grok out Action so we can do something with that too.
    body = StringIO(msg.get_payload())
    blocks = []
    headers = {}
    while 1:
        line = body.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            # A new recipient block
            blocks.append(headers)
            headers = {}
        try:
            hdr, val = line.split(':', 1)
        except ValueError:
            continue
        headers[hdr.lower()] = val.strip()
    # Make sure the last one is appended
    blocks.append(headers)
    # Now go through all the recipient blocks, looking for addresses that
    # are reported as bounced.  Preference order is Original-Recipient:
    # Final-Recipient:
    addrs = []
    for headers in blocks:
        # Should we treat delayed bounces the same?  Yes, because if the
        # transient problem clears up, they should get unbounced.
        if headers.get('action', '').lower() not in ('failed', 'failure',
                                                     'delayed'):
            # Some non-permanent failure, so ignore this block
            continue
        val = headers.get('original-recipient',
                          headers.get('final-recipient'))
        if val:
            addrs.append(parseaddr(val))
    return filter(None, addrs)



def process(msg):
    # The report-type parameter should be "delivery-status", but it seems that
    # some DSN generating MTAs don't include this on the Content-Type: header,
    # so let's relax the test a bit.
    if not msg.ismultipart() or msg.getsubtype() <> 'report':
        return None
    return check(msg)
