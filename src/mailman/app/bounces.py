# Copyright (C) 2007-2011 by the Free Software Foundation, Inc.
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
    'scan_message',
    ]

import logging

from email.mime.message import MIMEMessage
from email.mime.text import MIMEText

from mailman.app.finder import find_components
from mailman.core.i18n import _
from mailman.email.message import UserNotification
from mailman.interfaces.bounce import IBounceDetector
from mailman.utilities.string import oneline

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



def scan_message(mlist, msg):
    """Scan all the message for heuristically determined bounce addresses.

    :param mlist: The mailing list.
    :type mlist: `IMailingList`
    :param msg: The bounce message to scan.
    :type msg: `Message`
    :return: The set of bouncing addresses found in the scanned message.  The
        set will be empty if no addresses were found.
    :rtype: set
    """
    for detector_class in find_components('mailman.bouncers', IBounceDetector):
        addresses = detector_class().process(msg)
        # Detectors may return None or an empty sequence to signify that no
        # addresses have been found.
        if addresses:
            return set(addresses)
    return set()
