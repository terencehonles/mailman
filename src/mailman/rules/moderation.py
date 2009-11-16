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

"""Membership related rules."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Moderation',
    'NonMember',
    ]


from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.rules import IRule



class Moderation:
    """The member moderation rule."""
    implements(IRule)

    name = 'moderation'
    description = _('Match messages sent by moderated members.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        for sender in msg.senders:
            member = mlist.members.get_member(sender)
            if member is not None and member.is_moderated:
                return True
        return False



class NonMember:
    """The non-membership rule."""
    implements(IRule)

    name = 'non-member'
    description = _('Match messages sent by non-members.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        for sender in msg.senders:
            if mlist.members.get_member(sender) is not None:
                # The sender is a member of the mailing list.
                return False
        return True
