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

"""The terminal 'discard' chain."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'DiscardChain',
    ]


import logging

from mailman.chains.base import TerminalChainBase
from mailman.core.i18n import _


log = logging.getLogger('mailman.vette')



class DiscardChain(TerminalChainBase):
    """Discard a message."""

    name = 'discard'
    description = _('Discard a message and stop processing.')

    def _process(self, mlist, msg, msgdata):
        """See `TerminalChainBase`."""
        log.info('DISCARD: %s', msg.get('message-id', 'n/a'))
        # Nothing more needs to happen.
