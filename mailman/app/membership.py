# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""Application support for membership management."""

from __future__ import with_statement

from email.utils import formataddr

from mailman import Errors
from mailman import Message
from mailman import Utils
from mailman import i18n
from mailman.configuration import config
from mailman.interfaces import DeliveryMode, MemberRole

_ = i18n._



def add_member(mlist, address, realname, password, delivery_mode, language,
               ack=None, admin_notif=None, text=''):
    """Add a member right now.

    The member's subscription must be approved by what ever policy the
    list enforces.

    ack is a flag that specifies whether the user should get an
    acknowledgement of their being subscribed.  Default is to use the
    list's default flag value.

    admin_notif is a flag that specifies whether the list owner should get
    an acknowledgement of this subscription.  Default is to use the list's
    default flag value.
    """
    # Set up default flag values
    if ack is None:
        ack = mlist.send_welcome_msg
    if admin_notif is None:
        admin_notif = mlist.admin_notify_mchanges
    # Let's be extra cautious.
    Utils.ValidateEmail(address)
    if mlist.members.get_member(address) is not None:
        raise Errors.AlreadySubscribedError(address)
    # Check for banned address here too for admin mass subscribes and
    # confirmations.
    pattern = Utils.get_pattern(address, mlist.ban_list)
    if pattern:
        raise Errors.MembershipIsBanned(pattern)
    # Do the actual addition.  First, see if there's already a user linked
    # with the given address.
    user = config.db.user_manager.get_user(address)
    if user is None:
        # A user linked to this address does not yet exist.  Is the address
        # itself known but just not linked to a user?
        address_obj = config.db.user_manager.get_address(address)
        if address_obj is None:
            # Nope, we don't even know about this address, so create both the
            # user and address now.
            user = config.db.user_manager.create_user(address, realname)
            # Do it this way so we don't have to flush the previous change.
            address_obj = list(user.addresses)[0]
        else:
            # The address object exists, but it's not linked to a user.
            # Create the user and link it now.
            user = config.db.user_manager.create_user()
            user.real_name = (realname if realname else address_obj.real_name)
            user.link(address_obj)
        # Since created the user, then the member,  and set preferences on the
        # appropriate object.
        user.password = password
        user.preferences.preferred_language = language
        member = address_obj.subscribe(mlist, MemberRole.member)
        member.preferences.delivery_mode = delivery_mode
    else:
        # The user exists and is linked to the address.
        for address_obj in user.addresses:
            if address_obj.address == address:
                break
        else:
            raise AssertionError(
                'User should have had linked address: %s', address)
        # Create the member and set the appropriate preferences.
        member = address_obj.subscribe(mlist, MemberRole.member)
        member.preferences.preferred_language = language
        member.preferences.delivery_mode = delivery_mode
##     mlist.setMemberOption(email, config.Moderate,
##                          mlist.default_member_moderation)
    # Send notifications.
    if ack:
        send_welcome_message(mlist, address, language, delivery_mode, text)
    if admin_notif:
        with i18n.using_language(mlist.preferred_language):
            subject = _('$mlist.real_name subscription notification')
        if isinstance(realname, unicode):
            realname = realname.encode(Utils.GetCharSet(language), 'replace')
        text = Utils.maketext(
            'adminsubscribeack.txt',
            {'listname' : mlist.real_name,
             'member'   : formataddr((realname, address)),
             }, mlist=mlist)
        msg = Message.OwnerNotification(mlist, subject, text)
        msg.send(mlist)



def send_welcome_message(mlist, address, language, delivery_mode, text=''):
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
            }, lang=language, mlist=mlist)
    if delivery_mode is not DeliveryMode.regular:
        digmode = _(' (Digest mode)')
    else:
        digmode = ''
    msg = Message.UserNotification(
        address, mlist.request_address,
        _('Welcome to the "$mlist.real_name" mailing list${digmode}'),
        text, language)
    msg['X-No-Archive'] = 'yes'
    msg.send(mlist, verp=config.VERP_PERSONALIZED_DELIVERIES)



def delete_member(mlist, address, admin_notif=None, userack=None):
    if userack is None:
        userack = mlist.send_goodbye_msg
    if admin_notif is None:
        admin_notif = mlist.admin_notify_mchanges
    # Delete a member, for which we know the approval has been made
    member = mlist.members.get_member(address)
    language = member.preferred_language
    member.unsubscribe()
    # And send an acknowledgement to the user...
    if userack:
        send_goodbye_message(mlist, address, language)
    # ...and to the administrator.
    if admin_notif:
        user = config.db.user_manager.get_user(address)
        realname = user.real_name
        subject = _('$mlist.real_name unsubscription notification')
        text = Utils.maketext(
            'adminunsubscribeack.txt',
            {'listname': mlist.real_name,
             'member'  : formataddr((realname, address)),
             }, mlist=mlist)
        msg = Message.OwnerNotification(mlist, subject, text)
        msg.send(mlist)



def send_goodbye_message(mlist, address, language):
    if mlist.goodbye_msg:
        goodbye = Utils.wrap(mlist.goodbye_msg) + '\n'
    else:
        goodbye = ''
    msg = Message.UserNotification(
        address, mlist.bounces_address,
        _('You have been unsubscribed from the $mlist.real_name mailing list'),
        goodbye, language)
    msg.send(mlist, verp=config.VERP_PERSONALIZED_DELIVERIES)
