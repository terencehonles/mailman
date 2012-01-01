# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""The header-matching chain."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'HeaderMatchChain',
    ]


import re
import logging
import itertools

from zope.interface import implements

from mailman.chains.base import Chain, Link
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.chain import IChainIterator, LinkAction
from mailman.interfaces.rules import IRule


log = logging.getLogger('mailman.vette')



def make_link(entry):
    """Create a Link object.

    :param entry: a 2- or 3-tuple describing a link.  If a 2-tuple, it is a
        header and a pattern, and a default chain of 'hold' will be used.  If
        a 3-tuple, the third item is the chain name to use.
    :return: an ILink.
    """
    if len(entry) == 2:
        header, pattern = entry
        chain_name = 'hold'
    elif len(entry) == 3:
        header, pattern, chain_name = entry
        # We don't assert that the chain exists here because the jump
        # chain may not yet have been created.
    else:
        raise AssertionError('Bad link description: {0}'.format(entry))
    rule = HeaderMatchRule(header, pattern)
    chain = config.chains[chain_name]
    return Link(rule, LinkAction.jump, chain)



class HeaderMatchRule:
    """Header matching rule used by header-match chain."""
    implements(IRule)

    # Sequential rule counter.
    _count = 1

    def __init__(self, header, pattern):
        self._header = header
        self._pattern = pattern
        self.name = 'header-match-{0:02}'.format(HeaderMatchRule._count)
        HeaderMatchRule._count += 1
        self.description = '{0}: {1}'.format(header, pattern)
        # XXX I think we should do better here, somehow recording that a
        # particular header matched a particular pattern, but that gets ugly
        # with RFC 2822 headers.  It also doesn't match well with the rule
        # name concept.  For now, we just record the rather useless numeric
        # rule name.  I suppose we could do the better hit recording in the
        # check() method, and set self.record = False.
        self.record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        for value in msg.get_all(self._header, []):
            if re.search(self._pattern, value, re.IGNORECASE):
                return True
        return False



class HeaderMatchChain(Chain):
    """Default header matching chain.

    This could be extended by header match rules in the database.
    """

    def __init__(self):
        super(HeaderMatchChain, self).__init__(
            'header-match', _('The built-in header matching chain'))
        # The header match rules are not global, so don't register them.
        # These are the only rules that the header match chain can execute.
        self._links = []
        # Initialize header check rules with those from the global
        # HEADER_MATCHES variable.
        for entry in config.header_matches:
            self._links.append(make_link(entry))
        # Keep track of how many global header matching rules we've seen.
        # This is so the flush() method will only delete those that were added
        # via extend() or append_link().
        self._permanent_link_count = len(self._links)

    def extend(self, header, pattern, chain_name='hold'):
        """Extend the existing header matches.

        :param header: The case-insensitive header field name.
        :param pattern: The pattern to match the header's value again.  The
            match is not anchored and is done case-insensitively.
        :param chain: Option chain to jump to if the pattern matches any of
            the named header values.  If not given, the 'hold' chain is used.
        """
        self._links.append(make_link((header, pattern, chain_name)))

    def flush(self):
        """See `IMutableChain`."""
        del self._links[self._permanent_link_count:]

    def get_links(self, mlist, msg, msgdata):
        """See `IChain`."""
        list_iterator = HeaderMatchIterator(mlist)
        return itertools.chain(iter(self._links), iter(list_iterator))

    def __iter__(self):
        for link in self._links:
            yield link



class HeaderMatchIterator:
    """An iterator of both the global and list-specific chain links."""

    implements(IChainIterator)

    def __init__(self, mlist):
        self._mlist = mlist

    def __iter__(self):
        """See `IChainIterator`."""
        for entry in self._mlist.header_matches:
            yield make_link(entry)
