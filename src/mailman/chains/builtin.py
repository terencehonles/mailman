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

"""The default built-in starting chain."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'BuiltInChain',
    ]


import logging

from zope.interface import implements

from mailman.chains.base import Link
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.chain import IChain, LinkAction


log = logging.getLogger('mailman.vette')



class BuiltInChain:
    """Default built-in chain."""

    implements(IChain)

    name = 'default-posting-chain'
    description = _('The built-in moderation chain.')

    _link_descriptions = (
        ('approved', LinkAction.jump, 'accept'),
        ('emergency', LinkAction.jump, 'hold'),
        ('loop', LinkAction.jump, 'discard'),
        # Determine whether the member or nonmember has an action shortcut.
        ('member-moderation', LinkAction.jump, 'moderation'),
        # Do all of the following before deciding whether to hold the message.
        ('administrivia', LinkAction.defer, None),
        ('implicit-dest', LinkAction.defer, None),
        ('max-recipients', LinkAction.defer, None),
        ('max-size', LinkAction.defer, None),
        ('news-moderation', LinkAction.defer, None),
        ('no-subject', LinkAction.defer, None),
        ('suspicious-header', LinkAction.defer, None),
        # Now if any of the above hit, jump to the hold chain.
        ('any', LinkAction.jump, 'hold'),
        # Take a detour through the header matching chain, which we'll create
        # later.
        ('truth', LinkAction.detour, 'header-match'),
        # Check for nonmember moderation.
        ('nonmember-moderation', LinkAction.jump, 'moderation'),
        # Finally, the builtin chain jumps to acceptance.
        ('truth', LinkAction.jump, 'accept'),
        )

    def __init__(self):
        self._cached_links = None

    def get_links(self, mlist, msg, msgdata):
        """See `IChain`."""
        if self._cached_links is None:
            self._cached_links = links = []
            for rule_name, action, chain_name in self._link_descriptions:
                # Get the named rule.
                rule = config.rules[rule_name]
                # Get the chain, if one is defined.
                chain = (None if chain_name is None
                         else config.chains[chain_name])
                links.append(Link(rule, action, chain))
        return iter(self._cached_links)
