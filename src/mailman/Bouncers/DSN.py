# Copyright (C) 1998-2009 by the Free Software Foundation, Inc.
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

"""Parse RFC 3464 (i.e. DSN) bounce formats.

RFC 3464 obsoletes 1894 which was the old DSN standard.  This module has not
been audited for differences between the two.
"""

from email.Iterators import typed_subpart_iterator
from email.Utils import parseaddr

from mailman.Bouncers.BouncerAPI import Stop



def check(msg):
    # Iterate over each message/delivery-status subpart
    addrs = []
    for part in typed_subpart_iterator(msg, 'message', 'delivery-status'):
        if not part.is_multipart():
            # Huh?
            continue
        # Each message/delivery-status contains a list of Message objects
        # which are the header blocks.  Iterate over those too.
        for msgblock in part.get_payload():
            # We try to dig out the Original-Recipient (which is optional) and
            # Final-Recipient (which is mandatory, but may not exactly match
            # an address on our list).  Some MTA's also use X-Actual-Recipient
            # as a synonym for Original-Recipient, but some apparently use
            # that for other purposes :(
            #
            # Also grok out Action so we can do something with that too.
            action = msgblock.get('action', '').lower()
            # Some MTAs have been observed that put comments on the action.
            if action.startswith('delayed'):
                return Stop
            if not action.startswith('fail'):
                # Some non-permanent failure, so ignore this block
                continue
            params = []
            foundp = False
            for header in ('original-recipient', 'final-recipient'):
                for k, v in msgblock.get_params([], header):
                    if k.lower() == 'rfc822':
                        foundp = True
                    else:
                        params.append(k)
                if foundp:
                    # Note that params should already be unquoted.
                    addrs.extend(params)
                    break
                else:
                    # MAS: This is a kludge, but SMTP-GATEWAY01.intra.home.dk
                    # has a final-recipient with an angle-addr and no
                    # address-type parameter at all. Non-compliant, but ...
                    for param in params:
                        if param.startswith('<') and param.endswith('>'):
                            addrs.append(param[1:-1])
    # Uniquify
    rtnaddrs = {}
    for a in addrs:
        if a is not None:
            realname, a = parseaddr(a)
            rtnaddrs[a] = True
    return rtnaddrs.keys()



def process(msg):
    # A DSN has been seen wrapped with a "legal disclaimer" by an outgoing MTA
    # in a multipart/mixed outer part.
    if msg.is_multipart() and msg.get_content_subtype() == 'mixed':
        msg = msg.get_payload()[0]
    # The above will suffice if the original message 'parts' were wrapped with
    # the disclaimer added, but the original DSN can be wrapped as a
    # message/rfc822 part.  We need to test that too.
    if msg.is_multipart() and msg.get_content_type() == 'message/rfc822':
        msg = msg.get_payload()[0]
    # The report-type parameter should be "delivery-status", but it seems that
    # some DSN generating MTAs don't include this on the Content-Type: header,
    # so let's relax the test a bit.
    if not msg.is_multipart() or msg.get_content_subtype() <> 'report':
        return None
    return check(msg)
