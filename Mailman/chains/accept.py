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

"""The terminal 'accept' chain."""

__all__ = ['AcceptChain']
__metaclass__ = type

import logging

from Mailman.chains.base import TerminalChainBase
from Mailman.configuration import config
from Mailman.i18n import _
from Mailman.queue import Switchboard


log = logging.getLogger('mailman.vette')
SEMISPACE = '; '



class AcceptChain(TerminalChainBase):
    """Accept the message for posting."""

    name = 'accept'
    description = _('Accept a message.')

    def _process(self, mlist, msg, msgdata):
        """See `TerminalChainBase`."""
        # Start by decorating the message with a header that contains a list
        # of all the rules that matched.  These metadata could be None or an
        # empty list.
        rule_hits = msgdata.get('rule_hits')
        if rule_hits:
            msg['X-Mailman-Rule-Hits'] = SEMISPACE.join(rule_hits)
        rule_misses = msgdata.get('rule_misses')
        if rule_misses:
            msg['X-Mailman-Rule-Misses'] = SEMISPACE.join(rule_misses)
        accept_queue = Switchboard(config.PREPQUEUE_DIR)
        accept_queue.enqueue(msg, msgdata)
        log.info('ACCEPT: %s', msg.get('message-id', 'n/a'))
