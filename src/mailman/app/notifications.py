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

"""Sending notifications."""

from __future__ import unicode_literals

__metaclass__ = type
__all__ = [
    'send_admin_subscription_notice',
    'send_goodbye_message',
    'send_welcome_message',
    ]


from email.utils import formataddr
from lazr.config import as_boolean

from mailman import Utils
from mailman.config import config
from mailman.core.i18n import _
from mailman.email.message import OwnerNotification, UserNotification
from mailman.interfaces.member import DeliveryMode



def send_welcome_message(mlist, address, language, delivery_mode, text=''):
    """Send a welcome message to a subscriber.

    Prepending to the standard welcome message template is the mailing list's
    welcome message, if there is one.

    :param mlist: the mailing list
    :type mlist: IMailingList
    :param address: The address to respond to
    :type address: string
    :param language: the language of the response
    :type language: string
    :param delivery_mode: the type of delivery the subscriber is getting
    :type delivery_mode: DeliveryMode
    """
    if mlist.welcome_msg:
        welcome = Utils.wrap(mlist.welcome_msg) + '\n'
    else:
        welcome = ''
    # Find the IMember object which is subscribed to the mailing list, because
    # from there, we can get the member's options url.
    member = mlist.members.get_member(address)
    options_url = member.options_url
    # Get the text from the template.
    text += Utils.maketext(
        'subscribeack.txt', {
            'real_name'         : mlist.real_name,
            'posting_address'   : mlist.fqdn_listname,
            'listinfo_url'      : mlist.script_url('listinfo'),
            'optionsurl'        : options_url,
            'request_address'   : mlist.request_address,
            'welcome'           : welcome,
            }, lang=language.code, mlist=mlist)
    if delivery_mode is not DeliveryMode.regular:
        digmode = _(' (Digest mode)')
    else:
        digmode = ''
    msg = UserNotification(
        address, mlist.request_address,
        _('Welcome to the "$mlist.real_name" mailing list${digmode}'),
        text, language)
    msg['X-No-Archive'] = 'yes'
    msg.send(mlist, verp=as_boolean(config.mta.verp_personalized_deliveries))



def send_goodbye_message(mlist, address, language):
    """Send a goodbye message to a subscriber.

    Prepending to the standard goodbye message template is the mailing list's
    goodbye message, if there is one.

    :param mlist: the mailing list
    :type mlist: IMailingList
    :param address: The address to respond to
    :type address: string
    :param language: the language of the response
    :type language: string
    """
    if mlist.goodbye_msg:
        goodbye = Utils.wrap(mlist.goodbye_msg) + '\n'
    else:
        goodbye = ''
    msg = UserNotification(
        address, mlist.bounces_address,
        _('You have been unsubscribed from the $mlist.real_name mailing list'),
        goodbye, language)
    msg.send(mlist, verp=as_boolean(config.mta.verp_personalized_deliveries))



def send_admin_subscription_notice(mlist, address, full_name, language):
    """Send the list administrators a subscription notice.

    :param mlist: the mailing list
    :type mlist: IMailingList
    :param address: the address being subscribed
    :type address: string
    :param full_name: the name of the subscriber
    :type full_name: string
    :param language: the language of the address's realname
    :type language: string
    """
    with _.using(mlist.preferred_language.code):
        subject = _('$mlist.real_name subscription notification')
    full_name = full_name.encode(language.charset, 'replace')
    text = Utils.maketext(
        'adminsubscribeack.txt',
        {'listname' : mlist.real_name,
         'member'   : formataddr((full_name, address)),
         }, mlist=mlist)
    msg = OwnerNotification(mlist, subject, text)
    msg.send(mlist)
