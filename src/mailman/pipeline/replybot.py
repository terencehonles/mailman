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

"""Handler for automatic responses."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Replybot',
    ]


import logging

from zope.component import getUtility
from zope.interface import implements

from mailman.core.i18n import _
from mailman.email.message import UserNotification
from mailman.interfaces.autorespond import (
    ALWAYS_REPLY, IAutoResponseSet, Response, ResponseAction)
from mailman.interfaces.handler import IHandler
from mailman.interfaces.usermanager import IUserManager
from mailman.utilities.datetime import today
from mailman.utilities.string import expand, wrap


log = logging.getLogger('mailman.error')



class Replybot:
    """Send automatic responses."""

    implements(IHandler)

    name = 'replybot'
    description = _('Send automatic responses.')

    def process(self, mlist, msg, msgdata):
        """See `IHandler`."""
        # There are several cases where the replybot is short-circuited:
        # * the original message has an "X-Ack: No" header
        # * the message has a Precedence header with values bulk, junk, or
        #   list, and there's no explicit "X-Ack: yes" header
        # * the message metadata has a true 'noack' key
        ack = msg.get('x-ack', '').lower()
        if ack == 'no' or msgdata.get('noack'):
            return
        precedence = msg.get('precedence', '').lower()
        if ack != 'yes' and precedence in ('bulk', 'junk', 'list'):
            return
        # Check to see if the list is even configured to autorespond to this
        # email message.  Note: the incoming message processors should set the
        # destination key in the message data.
        if msgdata.get('to_owner'):
            if mlist.autorespond_owner is ResponseAction.none:
                return
            response_type = Response.owner
            response_text = mlist.autoresponse_owner_text
        elif msgdata.get('to_request'):
            if mlist.autorespond_requests is ResponseAction.none:
                return
            response_type = Response.command
            response_text = mlist.autoresponse_request_text
        elif msgdata.get('to_list'):
            if mlist.autorespond_postings is ResponseAction.none:
                return
            response_type = Response.postings
            response_text = mlist.autoresponse_postings_text
        else:
            # There are no automatic responses for any other destination.
            return
        # Now see if we're in the grace period for this sender.  grace_period
        # = 0 means always automatically respond, as does an "X-Ack: yes"
        # header (useful for debugging).
        response_set = IAutoResponseSet(mlist)
        user_manager = getUtility(IUserManager)
        address = user_manager.get_address(msg.sender)
        if address is None:
            address = user_manager.create_address(msg.sender)
        grace_period = mlist.autoresponse_grace_period
        if grace_period > ALWAYS_REPLY and ack != 'yes':
            last = response_set.last_response(address, response_type)
            if last is not None and last.date_sent + grace_period > today():
                return
        # Okay, we know we're going to respond to this sender, craft the
        # message, send it, and update the database.
        display_name = mlist.display_name
        subject = _(
            'Auto-response for your message to the "$display_name" '
            'mailing list')
        # Do string interpolation into the autoresponse text
        d = dict(list_name = mlist.list_name,
                 display_name = display_name,
                 listurl = mlist.script_url('listinfo'),
                 requestemail = mlist.request_address,
                 owneremail = mlist.owner_address,
                 )
        # Interpolation and Wrap the response text.
        text = wrap(expand(response_text, d))
        outmsg = UserNotification(msg.sender, mlist.bounces_address,
                                  subject, text, mlist.preferred_language)
        outmsg['X-Mailer'] = _('The Mailman Replybot')
        # prevent recursions and mail loops!
        outmsg['X-Ack'] = 'No'
        outmsg.send(mlist)
        response_set.response_sent(address, response_type)
