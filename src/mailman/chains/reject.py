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

"""The terminal 'reject' chain."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'RejectChain',
    'RejectNotification',
    ]


import logging
from zope.event import notify

from mailman.app.bounces import bounce_message
from mailman.chains.base import ChainNotification, TerminalChainBase
from mailman.core.i18n import _


log = logging.getLogger('mailman.vette')
SEMISPACE = '; '



class RejectNotification(ChainNotification):
    """A notification event signaling that a message is being rejected."""



class RejectChain(TerminalChainBase):
    """Reject/bounce a message."""

    name = 'reject'
    description = _('Reject/bounce a message and stop processing.')

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
        # XXX Exception/reason
        bounce_message(mlist, msg)
        log.info('REJECT: %s', msg.get('message-id', 'n/a'))
        notify(RejectNotification(mlist, msg, msgdata, self))
