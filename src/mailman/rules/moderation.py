# Copyright (C) 2007-2010 by the Free Software Foundation, Inc.
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
    ]


from zope.interface import implements

from mailman.core.i18n import _
from mailman.interfaces.action import Action
from mailman.interfaces.rules import IRule



class Moderation:
    """The member moderation rule."""
    implements(IRule)

    name = 'moderation'
    description = _('Match messages sent by moderated members and nonmembers.')
    record = True

    def check(self, mlist, msg, msgdata):
        """See `IRule`."""
        for sender in msg.senders:
            member = mlist.members.get_member(sender)
            action = (Action.defer if member is None
                      else member.moderation_action)
            if action is not Action.defer:
                # We must stringify the moderation action so that it can be
                # stored in the pending request table.
                msgdata['moderation_action'] = action.enumname
                msgdata['moderation_sender'] = sender
                return True
        for sender in msg.senders:
            nonmember = mlist.nonmembers.get_member(sender)
            action = (Action.defer if nonmember is None
                      else nonmember.moderation_action)
            if action is not Action.defer:
                # We must stringify the moderation action so that it can be
                # stored in the pending request table.
                msgdata['moderation_action'] = action.enumname
                msgdata['moderation_sender'] = sender
                return True
        # XXX This is not correct.  If the sender is neither a member nor a
        # nonmember, we need to register them as a nonmember and give them the
        # default action.
        return False
