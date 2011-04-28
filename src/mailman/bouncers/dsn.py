# Copyright (C) 1998-2011 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'DSN',
    ]


from email.iterators import typed_subpart_iterator
from email.utils import parseaddr
from zope.interface import implements

from mailman.interfaces.bounce import IBounceDetector, Stop



def check(msg):
    # Iterate over each message/delivery-status subpart.
    failed_addresses = []
    delayed_addresses = []
    for part in typed_subpart_iterator(msg, 'message', 'delivery-status'):
        if not part.is_multipart():
            # Huh?
            continue
        # Each message/delivery-status contains a list of Message objects
        # which are the header blocks.  Iterate over those too.
        for msgblock in part.get_payload():
            address_set = None
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
                address_set = delayed_addresses
            elif action.startswith('fail'):
                address_set = failed_addresses
            else:
                # Some non-permanent failure, so ignore this block.
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
                    address_set.extend(params)
                    break
                else:
                    # MAS: This is a kludge, but SMTP-GATEWAY01.intra.home.dk
                    # has a final-recipient with an angle-addr and no
                    # address-type parameter at all. Non-compliant, but ...
                    for param in params:
                        if param.startswith('<') and param.endswith('>'):
                            address_set.append(param[1:-1])
    # There may be both delayed and failed addresses.  If there are any failed
    # addresses, return those, otherwise just stop processing.
    if len(failed_addresses) == 0:
        if len(delayed_addresses) == 0:
            return set()
        else:
            return Stop
    return set(parseaddr(address)[1] for address in failed_addresses
               if address is not None)



class DSN:
    """Parse RFC 3464 (i.e. DSN) bounce formats."""

    implements(IBounceDetector)

    def process(self, msg):
        return check(msg)
        ## # A DSN has been seen wrapped with a "legal disclaimer" by an outgoing
        ## # MTA in a multipart/mixed outer part.
        ## if msg.is_multipart() and msg.get_content_subtype() == 'mixed':
        ##     msg = msg.get_payload()[0]
        ## # The above will suffice if the original message 'parts' were wrapped
        ## # with the disclaimer added, but the original DSN can be wrapped as a
        ## # message/rfc822 part.  We need to test that too.
        ## if msg.is_multipart() and msg.get_content_type() == 'message/rfc822':
        ##     msg = msg.get_payload()[0]
        ## # The report-type parameter should be "delivery-status", but it seems
        ## # that some DSN generating MTAs don't include this on the
        ## # Content-Type: header, so let's relax the test a bit.
        ## if not msg.is_multipart() or msg.get_content_subtype() <> 'report':
        ##     return set()
        ## return check(msg)
