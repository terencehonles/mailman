# Copyright (C) 2001-2009 by the Free Software Foundation, Inc.
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

"""Inject a message into a queue."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'inject_message',
    'inject_text',
    ]


# pylint doesn't understand absolute_import
# pylint: disable-msg=E0611,W0403
from email import message_from_string
from email.utils import formatdate, make_msgid

from mailman.config import config
from mailman.email.message import Message



def inject_message(mlist, msg, recips=None, switchboard=None, **kws):
    """Inject a message into a queue.

    :param mlist: The mailing list this message is destined for.
    :type mlist: IMailingList
    :param msg: The Message object to inject.
    :type msg: a Message object
    :param recips: Optional set of recipients to put into the message's
        metadata.
    :type recips: sequence of strings
    :param switchboard: Optional name of switchboard to inject this message
        into.  If not given, the 'in' switchboard is used.
    :type switchboard: string
    :param kws: Additional values for the message metadata.
    :type kws: dictionary
    """
    if switchboard is None:
        switchboard = 'in'
    # Since we're crafting the message from whole cloth, let's make sure this
    # message has a Message-ID.
    if 'message-id' not in msg:
        msg['Message-ID'] = make_msgid()
    # Ditto for Date: as required by RFC 2822.
    if 'date' not in msg:
        msg['Date'] = formatdate(localtime=True)
    msgdata = dict(
        listname=mlist.fqdn_listname,
        original_size=getattr(msg, 'original_size', len(msg.as_string())),
        )
    msgdata.update(kws)
    if recips is not None:
        msgdata['recipients'] = recips
    config.switchboards[switchboard].enqueue(msg, **msgdata)



def inject_text(mlist, text, recips=None, switchboard=None):
    """Inject a message into a queue.

    :param mlist: The mailing list this message is destined for.
    :type mlist: IMailingList
    :param text: The text of the message to inject.  This will be parsed into
        a Message object.
    :type text: string
    :param recips: Optional set of recipients to put into the message's
        metadata.
    :type recips: sequence of strings
    :param switchboard: Optional name of switchboard to inject this message
        into.  If not given, the 'in' switchboard is used.
    :type switchboard: string
    """
    message = message_from_string(text, Message)
    message.original_size = len(text)
    inject_message(mlist, message, recips, switchboard)
