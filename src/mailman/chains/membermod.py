# Copyright (C) 2010 by the Free Software Foundation, Inc.
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

"""Member moderation chain.

When a member's moderation flag is set, the built-in chain jumps to this
chain, which just checks the mailing list's member moderation action.  Based
on this value, one of the normal termination chains is jumped to.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MemberModerationChain',
    ]


from zope.interface import implements

from mailman.chains.base import Link
from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.action import Action
from mailman.interfaces.chain import IChain, LinkAction



class MemberModerationChain:
    """Dynamically produce a link jumping to the appropriate terminal chain.

    The terminal chain will be one of the Accept, Hold, Discard, or Reject
    chains, based on the mailing list's member moderation action setting.
    """

    implements(IChain)

    name = 'member-moderation'
    description = _('Member moderation chain')
    is_abstract = False

    def get_links(self, mlist, msg, msgdata):
        """See `IChain`."""
        # defer and accept are not valid moderation actions.
        jump_chains = {
            Action.hold: 'hold',
            Action.reject: 'reject',
            Action.discard: 'discard',
            }
        chain_name = jump_chains.get(mlist.member_moderation_action)
        assert chain_name is not None, (
            '{0}: Invalid member_moderation_action: {1}'.format(
                mlist.fqdn_listname, mlist.member_moderation_action))
        truth = config.rules['truth']
        chain = config.chains[chain_name]
        return iter([
            Link(truth, LinkAction.jump, chain),
            ])
