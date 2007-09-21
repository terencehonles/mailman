# Copyright (C) 2007 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Application level auto-reply code."""

# XXX This should undergo a rewrite to move this functionality off of the
# mailing list.  The reply governor should really apply site-wide per
# recipient (I think).

from __future__ import with_statement

__all__ = [
    'autorespond_to_sender',
    ]

import logging
import datetime

from Mailman import Utils
from Mailman import i18n
from Mailman.configuration import config


log = logging.getLogger('mailman.vette')
_ = i18n._



def autorespond_to_sender(mlist, sender, lang=None):
    """Return True if Mailman should auto-respond to this sender.

    This is only consulted for messages sent to the -request address, or
    for posting hold notifications, and serves only as a safety value for
    mail loops with email 'bots.
    """
    if lang is None:
        lang = mlist.preferred_language
    if config.MAX_AUTORESPONSES_PER_DAY == 0:
        # Unlimited.
        return True
    today = datetime.date.today()
    info = mlist.hold_and_cmd_autoresponses.get(sender)
    if info is None or info[0] <> today:
        # This is the first time we've seen a -request/post-hold for this
        # sender today.
        mlist.hold_and_cmd_autoresponses[sender] = (today, 1)
        return True
    date, count = info
    if count < 0:
        # They've already hit the limit for today, and we've already notified
        # them of this fact, so there's nothing more to do.
        log.info('-request/hold autoresponse discarded for: %s', sender)
        return False
    if count >= config.MAX_AUTORESPONSES_PER_DAY:
        log.info('-request/hold autoresponse limit hit for: %s', sender)
        mlist.hold_and_cmd_autoresponses[sender] = (today, -1)
        # Send this notification message instead.
        text = Utils.maketext(
            'nomoretoday.txt',
            {'sender' : sender,
             'listname': mlist.fqdn_listname,
             'num' : count,
             'owneremail': mlist.owner_address,
             },
            lang=lang)
        with i18n.using_language(lang):
            msg = Message.UserNotification(
                sender, mlist.owner_address,
                _('Last autoresponse notification for today'),
                text, lang=lang)
        msg.send(mlist)
        return False
    mlist.hold_and_cmd_autoresponses[sender] = (today, count + 1)
    return True

