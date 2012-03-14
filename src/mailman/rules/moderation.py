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

"""Membership related rules."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MemberModeration',
    'NonmemberModeration',
    ]


from zope.component import getUtility
from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.action import Action
from mailman.interfaces.member import MemberRole
from mailman.interfaces.rules import IRule
from mailman.interfaces.usermanager import IUserManager



class MemberModeration:
    """The member moderation rule."""
    implements(IRule)

    name = 'member-moderation'
    description = _('Match messages sent by moderated members.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        for sender in msg.senders:
            member = mlist.members.get_member(sender)
            action = (None if member is None
                      else member.moderation_action)
            if action is Action.defer:
                # The regular moderation rules apply.
                return False
            elif action is not None:
                # We must stringify the moderation action so that it can be
                # stored in the pending request table.
                msgdata['moderation_action'] = action.name
                msgdata['moderation_sender'] = sender
                return True
        # The sender is not a member so this rule does not match.
        return False



class NonmemberModeration:
    """The nonmember moderation rule."""
    implements(IRule)

    name = 'nonmember-moderation'
    description = _('Match messages sent by nonmembers.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        user_manager = getUtility(IUserManager)
        # First ensure that all senders are already either members or
        # nonmembers.  If they are not subscribed in some role to the mailing
        # list, make them nonmembers.
        for sender in msg.senders:
            if (mlist.members.get_member(sender) is None and
                mlist.nonmembers.get_member(sender) is None):
                # The address is neither a member nor nonmember.
                address = user_manager.get_address(sender)
                assert address is not None, (
                    'Posting address is not registered: {0}'.format(sender))
                mlist.subscribe(address, MemberRole.nonmember)
        # Do nonmember moderation check.
        for sender in msg.senders:
            nonmember = mlist.nonmembers.get_member(sender)
            action = (None if nonmember is None
                      else nonmember.moderation_action)
            if action is Action.defer:
                # The regular moderation rules apply.
                return False
            elif action is not None:
                # We must stringify the moderation action so that it can be
                # stored in the pending request table.
                msgdata['moderation_action'] = action.name
                msgdata['moderation_sender'] = sender
                return True
        # The sender must be a member, so this rule does not match.
        return False
