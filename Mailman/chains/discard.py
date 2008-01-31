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

"""The terminal 'discard' chain."""

__all__ = ['DiscardChain']
__metaclass__ = type


import logging

from Mailman.chains.base import TerminalChainBase
from Mailman.i18n import _


log = logging.getLogger('mailman.vette')



class DiscardChain(TerminalChainBase):
    """Discard a message."""

    name = 'discard'
    description = _('Discard a message and stop processing.')

    def _process(self, mlist, msg, msgdata):
        """See `TerminalChainBase`."""
        log.info('DISCARD: %s', msg.get('message-id', 'n/a'))
        # Nothing more needs to happen.
