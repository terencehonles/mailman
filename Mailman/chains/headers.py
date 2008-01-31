# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""The header-matching chain."""

__all__ = ['HeaderMatchChain']
__metaclass__ = type


import re
import logging

from zope.interface import implements

from Mailman.interfaces import IRule, LinkAction
from Mailman.chains.base import Chain, Link
from Mailman.i18n import _
from Mailman.configuration import config


log = logging.getLogger('mailman.vette')



class HeaderMatchRule:
    """Header matching rule used by header-match chain."""
    implements(IRule)

    # Sequential rule counter.
    _count = 1

    def __init__(self, header, pattern):
        self._header = header
        self._pattern = pattern
        self.name = 'header-match-%002d' % HeaderMatchRule._count
        HeaderMatchRule._count += 1
        self.description = u'%s: %s' % (header, pattern)
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
        self._rules = {}
        # Initialize header check rules with those from the global
        # HEADER_MATCHES variable.
        for entry in config.HEADER_MATCHES:
            if len(entry) == 2:
                header, pattern = entry
                chain = 'hold'
            elif len(entry) == 3:
                header, pattern, chain = entry
                # We don't assert that the chain exists here because the jump
                # chain may not yet have been created.
            else:
                raise AssertionError(
                    'Bad entry for HEADER_MATCHES: %s' % entry)
            self.extend(header, pattern, chain)

    def extend(self, header, pattern, chain='hold'):
        """Extend the existing header matches.

        :param header: The case-insensitive header field name.
        :param pattern: The pattern to match the header's value again.  The
            match is not anchored and is done case-insensitively.
        :param chain: Option chain to jump to if the pattern matches any of
            the named header values.  If not given, the 'hold' chain is used.
        """
        rule = HeaderMatchRule(header, pattern)
        self._rules[rule.name] = rule
        link = Link(rule.name, LinkAction.jump, chain)
        self._links.append(link)

    def get_rule(self, name):
        """See `IChain`.

        Only local rules are findable by this chain.
        """
        return self._rules[name]
