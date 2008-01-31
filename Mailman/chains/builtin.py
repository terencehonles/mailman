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

"""The default built-in starting chain."""

__all__ = ['BuiltInChain']
__metaclass__ = type


import logging

from Mailman.interfaces import LinkAction
from Mailman.chains.base import Chain, Link
from Mailman.i18n import _


log = logging.getLogger('mailman.vette')



class BuiltInChain(Chain):
    """Default built-in chain."""

    def __init__(self):
        super(BuiltInChain, self).__init__(
            'built-in', _('The built-in moderation chain.'))
        self.append_link(Link('approved', LinkAction.jump, 'accept'))
        self.append_link(Link('emergency', LinkAction.jump, 'hold'))
        self.append_link(Link('loop', LinkAction.jump, 'discard'))
        # Do all of the following before deciding whether to hold the message
        # for moderation.
        self.append_link(Link('administrivia', LinkAction.defer))
        self.append_link(Link('implicit-dest', LinkAction.defer))
        self.append_link(Link('max-recipients', LinkAction.defer))
        self.append_link(Link('max-size', LinkAction.defer))
        self.append_link(Link('news-moderation', LinkAction.defer))
        self.append_link(Link('no-subject', LinkAction.defer))
        self.append_link(Link('suspicious-header', LinkAction.defer))
        # Now if any of the above hit, jump to the hold chain.
        self.append_link(Link('any', LinkAction.jump, 'hold'))
        # Take a detour through the self header matching chain, which we'll
        # create later.
        self.append_link(Link('truth', LinkAction.detour, 'header-match'))
        # Finally, the builtin chain selfs to acceptance.
        self.append_link(Link('truth', LinkAction.jump, 'accept'))
