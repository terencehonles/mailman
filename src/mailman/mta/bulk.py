# Copyright (C) 2009 by the Free Software Foundation, Inc.
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

"""Module stuff."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'BulkDelivery',
    ]


from itertools import chain

from zope.interface import implements

from mailman.config import config
from mailman.interfaces.mta import IMailTransportAgentDelivery
from mailman.mta.connection import Connection


# A mapping of top-level domains to bucket numbers.  The zeroth bucket is
# reserved for everything else.  At one time, these were the most common
# domains.
CHUNKMAP = dict(
    com=1,
    net=2,
    org=2,
    edu=3,
    us=3,
    ca=3,
    )



class BulkDelivery:
    """Deliver messages to the MTA in as few sessions as possible."""

    implements(IMailTransportAgentDelivery)

    def __init__(self, max_recipients=None):
        """Create a bulk deliverer.

        :param max_recipients: The maximum number of recipients per delivery
            chunk.  None, zero or less means to group all recipients into one
            big chunk.
        :type max_recipients: integer
        """
        self._max_recipients = (max_recipients
                                if max_recipients is not None
                                else 0)
        self._connection = Connection(
            config.mta.smtp_host, int(config.mta.smtp_port),
            self._max_recipients)

    def chunkify(self, recipients):
        """Split a set of recipients into chunks.

        The `max_recipients` argument given to the constructor specifies the
        maximum number of recipients in each chunk.

        :param recipients: The set of recipient email addresses
        :type recipients: sequence of email address strings
        :return: A list of chunks, where each chunk is a set containing no
            more than `max_recipients` number of addresses.  The chunk can
            contain fewer, and no packing is guaranteed.
        :rtype: list of sets of strings
        """
        if self._max_recipients <= 0:
            yield set(recipients)
            return
        # This algorithm was originally suggested by Chuq Von Rospach.  Start
        # by splitting the recipient addresses into top-level domain buckets,
        # using the "most common" domains.  Everything else ends up in the
        # zeroth bucket.
        by_bucket = {}
        for address in recipients:
            localpart, at, domain = address.partition('@')
            domain_parts = domain.split('.')
            bucket_number = CHUNKMAP.get(domain_parts[-1], 0)
            by_bucket.setdefault(bucket_number, set()).add(address)
        # Fill chunks by sorting the tld values by length.
        chunk = set()
        for tld_chunk in sorted(by_bucket.values(), key=len, reverse=True):
            while tld_chunk:
                chunk.add(tld_chunk.pop())
                if len(chunk) == self._max_recipients:
                    yield chunk
                    chunk = set()
            # Every tld bucket starts a new chunk, but only if non-empty
            if len(chunk) > 0:
                yield chunk
                chunk = set()
        # Be sure to include the last chunk, but only if it's non-empty.
        if len(chunk) > 0:
            yield chunk

    def deliver(self, mlist, msg, msgdata):
        """See `IMailTransportAgentDelivery`."""
        recipients = msgdata.get('recipients')
        if recipients is None:
            return
        for recipients in self.chunkify(msgdata['recipients']):
            self._connection.sendmail(
                'foo@example.com', recipients, msg.as_string())
