# Copyright (C) 1998-2012 by the Free Software Foundation, Inc.
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

"""Calculate the regular (i.e. non-digest) recipients of the message.

This module calculates the non-digest recipients for the message based on the
list's membership and configuration options.  It places the list of recipients
on the `recipients' attribute of the message.  This attribute is used by the
SendmailDeliver and BulkDeliver modules.
"""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'MemberRecipients',
    ]


from zope.interface import implements

from mailman.config import config
from mailman.core import errors
from mailman.core.i18n import _
from mailman.interfaces.handler import IHandler
from mailman.interfaces.member import DeliveryStatus
from mailman.utilities.string import wrap



class MemberRecipients:
    """Calculate the regular (i.e. non-digest) recipients of the message."""

    implements(IHandler)

    name = 'member-recipients'
    description = _('Calculate the regular recipients of the message.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        # Short circuit if we've already calculated the recipients list,
        # regardless of whether the list is empty or not.
        if 'recipients' in msgdata:
            return
        # Should the original sender should be included in the recipients list?
        include_sender = True
        member = mlist.members.get_member(msg.sender)
        if member and not member.receive_own_postings:
            include_sender = False
        # Support for urgent messages, which bypasses digests and disabled
        # delivery and forces an immediate delivery to all members Right Now.
        # We are specifically /not/ allowing the site admins password to work
        # here because we want to discourage the practice of sending the site
        # admin password through email in the clear. (see also Approve.py)
        #
        # XXX This is broken.
        missing = object()
        password = msg.get('urgent', missing)
        if password is not missing:
            if mlist.Authenticate((config.AuthListModerator,
                                   config.AuthListAdmin),
                                  password):
                recipients = mlist.getMemberCPAddresses(
                    mlist.getRegularMemberKeys() +
                    mlist.getDigestMemberKeys())
                msgdata['recipients'] = recipients
                return
            else:
                # Bad Urgent: password, so reject it instead of passing it on.
                # I think it's better that the sender know they screwed up
                # than to deliver it normally.
                text = _("""\
Your urgent message to the $mlist.display_name mailing list was not authorized
for delivery.  The original message as received by Mailman is attached.
""")
                raise errors.RejectMessage(wrap(text))
        # Calculate the regular recipients of the message
        recipients = set(member.address.email
                         for member in mlist.regular_members.members
                         if member.delivery_status == DeliveryStatus.enabled)
        # Remove the sender if they don't want to receive their own posts
        if not include_sender and member.address.email in recipients:
            recipients.remove(member.address.email)
        # Handle topic classifications
        do_topic_filters(mlist, msg, msgdata, recipients)
        # Bookkeeping
        msgdata['recipients'] = recipients



def do_topic_filters(mlist, msg, msgdata, recipients):
    """Filter out recipients based on topics."""
    if not mlist.topics_enabled:
        # MAS: if topics are currently disabled for the list, send to all
        # regardless of ReceiveNonmatchingTopics
        return
    hits = msgdata.get('topichits')
    zap_recipients = []
    if hits:
        # The message hit some topics, so only deliver this message to those
        # who are interested in one of the hit topics.
        for user in recipients:
            utopics = mlist.getMemberTopics(user)
            if not utopics:
                # This user is not interested in any topics, so they get all
                # postings.
                continue
            # BAW: Slow, first-match, set intersection!
            for topic in utopics:
                if topic in hits:
                    # The user wants this message
                    break
            else:
                # The user was interested in topics, but not any of the ones
                # this message matched, so zap him.
                zap_recipients.append(user)
    else:
        # The semantics for a message that did not hit any of the pre-canned
        # topics is to troll through the membership list, looking for users
        # who selected at least one topic of interest, but turned on
        # ReceiveNonmatchingTopics.
        for user in recipients:
            if not mlist.getMemberTopics(user):
                # The user did not select any topics of interest, so he gets
                # this message by default.
                continue
            if not mlist.getMemberOption(
                user, config.ReceiveNonmatchingTopics):
                # The user has interest in some topics, but elects not to
                # receive message that match no topics, so zap him.
                zap_recipients.append(user)
            # Otherwise, the user wants non-matching messages.
    # Prune out the non-receiving users
    for user in zap_recipients:
        recipients.remove(user)
