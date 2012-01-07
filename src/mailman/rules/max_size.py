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

"""The maximum message size rule."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MaximumSize',
    ]


from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.rules import IRule



class MaximumSize:
    """The implicit destination rule."""
    implements(IRule)

    name = 'max-size'
    description = _('Catch messages that are bigger than a specified maximum.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        if mlist.max_message_size == 0:
            return False
        assert hasattr(msg, 'original_size'), (
            'Message was not sized on initial parsing.')
        # The maximum size is specified in 1024 bytes.
        return msg.original_size / 1024.0 > mlist.max_message_size
