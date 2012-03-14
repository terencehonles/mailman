# Copyright (C) 2001-2012 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'inject_message',
    'inject_text',
    ]


from email import message_from_string
from email.utils import formatdate, make_msgid

from mailman.config import config
from mailman.email.message import Message
from mailman.utilities.email import add_message_hash



def inject_message(mlist, msg, recipients=None, switchboard=None, **kws):
    """Inject a message into a queue.

    If the message does not have a Message-ID header, one is added.  An
    X-Message-Id-Hash header is also always added.

    :param mlist: The mailing list this message is destined for.
    :type mlist: IMailingList
    :param msg: The Message object to inject.
    :type msg: a Message object
    :param recipients: Optional set of recipients to put into the message's
        metadata.
    :type recipients: sequence of strings
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
    add_message_hash(msg)
    # Ditto for Date: as required by RFC 2822.
    if 'date' not in msg:
        msg['Date'] = formatdate(localtime=True)
    msg.original_size = len(msg.as_string())
    msgdata = dict(
        listname=mlist.fqdn_listname,
        original_size=msg.original_size,
        )
    msgdata.update(kws)
    if recipients is not None:
        msgdata['recipients'] = recipients
    config.switchboards[switchboard].enqueue(msg, **msgdata)



def inject_text(mlist, text, recipients=None, switchboard=None, **kws):
    """Turn text into a message and inject that into a queue.

    If the text does not have a Message-ID header, one is added.  An
    X-Message-Id-Hash header is also always added.

    :param mlist: The mailing list this message is destined for.
    :type mlist: IMailingList
    :param text: The text of the message to inject.  This will be parsed into
        a Message object.
    :type text: byte string
    :param recipients: Optional set of recipients to put into the message's
        metadata.
    :type recipients: sequence of strings
    :param switchboard: Optional name of switchboard to inject this message
        into.  If not given, the 'in' switchboard is used.
    :type switchboard: string
    :param kws: Additional values for the message metadata.
    :type kws: dictionary
    """
    message = message_from_string(text, Message)
    inject_message(mlist, message, recipients, switchboard, **kws)
