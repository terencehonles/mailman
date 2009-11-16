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

"""Application level bounce handling."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'bounce_message',
    ]

import logging

from email.mime.message import MIMEMessage
from email.mime.text import MIMEText

from mailman.Utils import oneline
from mailman.core.i18n import _
from mailman.email.message import UserNotification

log = logging.getLogger('mailman.config')



def bounce_message(mlist, msg, e=None):
    """Bounce the message back to the original author.

    :param mlist: The mailing list that the message was posted to.
    :type mlist: `IMailingList`
    :param msg: The original message.
    :type msg: `email.message.Message`
    :param e: Optional exception causing the bounce.
    :type e: Exception
    """
    # Bounce a message back to the sender, with an error message if provided
    # in the exception argument.
    if msg.sender is None:
        # We can't bounce the message if we don't know who it's supposed to go
        # to.
        return
    subject = msg.get('subject', _('(no subject)'))
    subject = oneline(subject, mlist.preferred_language.charset)
    if e is None:
        notice = _('[No bounce details are available]')
    else:
        notice = _(e.notice)
    # Currently we always craft bounces as MIME messages.
    bmsg = UserNotification(msg.sender, mlist.owner_address, subject,
                            lang=mlist.preferred_language)
    # BAW: Be sure you set the type before trying to attach, or you'll get
    # a MultipartConversionError.
    bmsg.set_type('multipart/mixed')
    txt = MIMEText(notice, _charset=mlist.preferred_language.charset)
    bmsg.attach(txt)
    bmsg.attach(MIMEMessage(msg))
    bmsg.send(mlist)
