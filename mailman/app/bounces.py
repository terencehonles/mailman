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

__all__ = [
    'bounce_message',
    ]

import re
import logging

from email.mime.message import MIMEMessage
from email.mime.text import MIMEText
from email.utils import getaddresses

from mailman import Message
from mailman import Utils
from mailman.i18n import _

log = logging.getLogger('mailman.config')



def bounce_message(mlist, msg, e=None):
    # Bounce a message back to the sender, with an error message if provided
    # in the exception argument.
    sender = msg.get_sender()
    subject = msg.get('subject', _('(no subject)'))
    subject = Utils.oneline(subject,
                            Utils.GetCharSet(mlist.preferred_language))
    if e is None:
        notice = _('[No bounce details are available]')
    else:
        notice = _(e.notice)
    # Currently we always craft bounces as MIME messages.
    bmsg = Message.UserNotification(msg.get_sender(),
                                    mlist.owner_address,
                                    subject,
                                    lang=mlist.preferred_language)
    # BAW: Be sure you set the type before trying to attach, or you'll get
    # a MultipartConversionError.
    bmsg.set_type('multipart/mixed')
    txt = MIMEText(notice,
                   _charset=Utils.GetCharSet(mlist.preferred_language))
    bmsg.attach(txt)
    bmsg.attach(MIMEMessage(msg))
    bmsg.send(mlist)
