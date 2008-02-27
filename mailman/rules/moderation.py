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

"""Membership related rules."""

__all__ = [
    'Moderation',
    'NonMember',
    ]
__metaclass__ = type


from zope.interface import implements

from mailman.i18n import _
from mailman.interfaces import IRule



class Moderation:
    """The member moderation rule."""
    implements(IRule)

    name = 'moderation'
    description = _('Match messages sent by moderated members.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        for sender in msg.get_senders():
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
        for sender in msg.get_senders():
            if mlist.members.get_member(sender) is not None:
                # The sender is a member of the mailing list.
                return False
        return True
