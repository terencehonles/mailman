# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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

"""The terminal 'accept' chain."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AcceptChain',
    ]

import logging

from mailman.chains.base import TerminalChainBase
from mailman.config import config
from mailman.core.i18n import _


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
        accept_queue = config.switchboards['pipeline']
        accept_queue.enqueue(msg, msgdata)
        log.info('ACCEPT: %s', msg.get('message-id', 'n/a'))
