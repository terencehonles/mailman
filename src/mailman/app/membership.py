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

"""Application support for membership management."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'add_member',
    'delete_member',
    ]


from email.utils import formataddr
from zope.component import getUtility

from mailman import Utils
from mailman.app.notifications import send_goodbye_message
from mailman.core import errors
from mailman.core.i18n import _
from mailman.email.message import OwnerNotification
from mailman.email.validate import validate
from mailman.interfaces.member import AlreadySubscribedError, MemberRole
from mailman.interfaces.usermanager import IUserManager



def add_member(mlist, address, realname, password, delivery_mode, language):
    """Add a member right now.

    The member's subscription must be approved by whatever policy the list
    enforces.

    :param mlist: The mailing list to add the member to.
    :type mlist: `IMailingList`
    :param address: The address to subscribe.
    :type address: string
    :param realname: The subscriber's full name.
    :type realname: string
    :param password: The subscriber's password.
    :type password: string
    :param delivery_mode: The delivery mode the subscriber has chosen.
    :type delivery_mode: DeliveryMode
    :param language: The language that the subscriber is going to use.
    :type language: string
    """
    # Let's be extra cautious.
    validate(address)
    if mlist.members.get_member(address) is not None:
        raise AlreadySubscribedError(
            mlist.fqdn_listname, address, MemberRole.member)
    # Check for banned address here too for admin mass subscribes and
    # confirmations.
    pattern = Utils.get_pattern(address, mlist.ban_list)
    if pattern:
        raise errors.MembershipIsBanned(pattern)
    # Do the actual addition.  First, see if there's already a user linked
    # with the given address.
    user_manager = getUtility(IUserManager)
    user = user_manager.get_user(address)
    if user is None:
        # A user linked to this address does not yet exist.  Is the address
        # itself known but just not linked to a user?
        address_obj = user_manager.get_address(address)
        if address_obj is None:
            # Nope, we don't even know about this address, so create both the
            # user and address now.
            user = user_manager.create_user(address, realname)
            # Do it this way so we don't have to flush the previous change.
            address_obj = list(user.addresses)[0]
        else:
            # The address object exists, but it's not linked to a user.
            # Create the user and link it now.
            user = user_manager.create_user()
            user.real_name = (realname if realname else address_obj.real_name)
            user.link(address_obj)
        # Since created the user, then the member, and set preferences on the
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
                'User should have had linked address: {0}'.format(address))
        # Create the member and set the appropriate preferences.
        # pylint: disable-msg=W0631
        member = address_obj.subscribe(mlist, MemberRole.member)
        member.preferences.preferred_language = language
        member.preferences.delivery_mode = delivery_mode
##     mlist.setMemberOption(email, config.Moderate,
##                          mlist.default_member_moderation)



def delete_member(mlist, address, admin_notif=None, userack=None):
    """Delete a member right now.

    :param mlist: The mailing list to add the member to.
    :type mlist: `IMailingList`
    :param address: The address to subscribe.
    :type address: string
    :param admin_notif: Whether the list administrator should be notified that
        this member was deleted.
    :type admin_notif: bool, or None to let the mailing list's
        `admin_notify_mchange` attribute decide.
    """
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
        user = getUtility(IUserManager).get_user(address)
        realname = user.real_name
        subject = _('$mlist.real_name unsubscription notification')
        text = Utils.maketext(
            'adminunsubscribeack.txt',
            {'listname': mlist.real_name,
             'member'  : formataddr((realname, address)),
             }, mlist=mlist)
        msg = OwnerNotification(mlist, subject, text)
        msg.send(mlist)
