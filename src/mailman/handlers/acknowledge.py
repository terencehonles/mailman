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

"""Send an acknowledgment of the successful post to the sender.

This only happens if the sender has set their AcknowledgePosts attribute.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Acknowledge',
    ]


from zope.component import getUtility
from zope.interface import implements

from mailman.core.i18n import _
from mailman.email.message import UserNotification
from mailman.interfaces.handler import IHandler
from mailman.interfaces.languages import ILanguageManager
from mailman.utilities.i18n import make
from mailman.utilities.string import oneline



class Acknowledge:
    """Send an acknowledgment."""
    implements(IHandler)

    name = 'acknowledge'
    description = _("""Send an acknowledgment of a posting.""")

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        # Extract the sender's address and find them in the user database
        sender = msgdata.get('original_sender', msg.sender)
        member = mlist.members.get_member(sender)
        if member is None or not member.acknowledge_posts:
            # Either the sender is not a member, in which case we can't know
            # whether they want an acknowlegment or not, or they are a member
            # who definitely does not want an acknowlegment.
            return
        # Okay, they are a member that wants an acknowledgment of their post.
        # Give them their original subject.  BAW: do we want to use the
        # decoded header?
        original_subject = msgdata.get(
            'origsubj', msg.get('subject', _('(no subject)')))
        # Get the user's preferred language.
        language_manager = getUtility(ILanguageManager)
        language = (language_manager[msgdata['lang']]
                    if 'lang' in msgdata
                    else member.preferred_language)
        charset = language_manager[language.code].charset
        # Now get the acknowledgement template.
        display_name = mlist.display_name
        text = make('postack.txt',
                    mailing_list=mlist,
                    language=language.code,
                    wrap=False,
                    subject=oneline(original_subject, charset),
                    list_name=mlist.list_name,
                    display_name=display_name,
                    listinfo_url=mlist.script_url('listinfo'),
                    optionsurl=member.options_url,
                    )
        # Craft the outgoing message, with all headers and attributes
        # necessary for general delivery.  Then enqueue it to the outgoing
        # queue.
        subject = _('$display_name post acknowledgment')
        usermsg = UserNotification(sender, mlist.bounces_address,
                                   subject, text, language)
        usermsg.send(mlist)
