# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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
from flufl.password import lookup, make_secret
from zope.component import getUtility

from mailman.app.notifications import send_goodbye_message
from mailman.config import config
from mailman.core.i18n import _
from mailman.email.message import OwnerNotification
from mailman.interfaces.address import IEmailValidator
from mailman.interfaces.bans import IBanManager
from mailman.interfaces.member import (
    MemberRole, MembershipIsBannedError, NotAMemberError)
from mailman.interfaces.usermanager import IUserManager
from mailman.utilities.i18n import make



def add_member(mlist, email, display_name, password, delivery_mode, language,
               role=MemberRole.member):
    """Add a member right now.

    The member's subscription must be approved by whatever policy the list
    enforces.

    :param mlist: The mailing list to add the member to.
    :type mlist: `IMailingList`
    :param email: The email address to subscribe.
    :type email: str
    :param display_name: The subscriber's full name.
    :type display_name: str
    :param password: The subscriber's plain text password.
    :type password: str
    :param delivery_mode: The delivery mode the subscriber has chosen.
    :type delivery_mode: DeliveryMode
    :param language: The language that the subscriber is going to use.
    :type language: str
    :param role: The membership role for this subscription.
    :type role: `MemberRole`
    :return: The just created member.
    :rtype: `IMember`
    :raises AlreadySubscribedError: if the user is already subscribed to
        the mailing list.
    :raises InvalidEmailAddressError: if the email address is not valid.
    :raises MembershipIsBannedError: if the membership is not allowed.
    """
    # Let's be extra cautious.
    getUtility(IEmailValidator).validate(email)
    # Check to see if the email address is banned.
    if getUtility(IBanManager).is_banned(email, mlist.fqdn_listname):
        raise MembershipIsBannedError(mlist, email)
    # See if there's already a user linked with the given address.
    user_manager = getUtility(IUserManager)
    user = user_manager.get_user(email)
    if user is None:
        # A user linked to this address does not yet exist.  Is the address
        # itself known but just not linked to a user?
        address = user_manager.get_address(email)
        if address is None:
            # Nope, we don't even know about this address, so create both the
            # user and address now.
            user = user_manager.create_user(email, display_name)
            # Do it this way so we don't have to flush the previous change.
            address = list(user.addresses)[0]
        else:
            # The address object exists, but it's not linked to a user.
            # Create the user and link it now.
            user = user_manager.create_user()
            user.display_name = (
                display_name if display_name else address.display_name)
            user.link(address)
        # Encrypt the password using the currently selected scheme.  The
        # scheme is recorded in the hashed password string.
        scheme = lookup(config.passwords.password_scheme.upper())
        user.password = make_secret(password, scheme)
        user.preferences.preferred_language = language
        member = mlist.subscribe(address, role)
        member.preferences.delivery_mode = delivery_mode
    else:
        # The user exists and is linked to the address.
        for address in user.addresses:
            if address.email == email:
                break
        else:
            raise AssertionError(
                'User should have had linked address: {0}'.format(address))
        # Create the member and set the appropriate preferences.
        member = mlist.subscribe(address, role)
        member.preferences.preferred_language = language
        member.preferences.delivery_mode = delivery_mode
    return member



def delete_member(mlist, email, admin_notif=None, userack=None):
    """Delete a member right now.

    :param mlist: The mailing list to remove the member from.
    :type mlist: `IMailingList`
    :param email: The email address to unsubscribe.
    :type email: string
    :param admin_notif: Whether the list administrator should be notified that
        this member was deleted.
    :type admin_notif: bool, or None to let the mailing list's
        `admin_notify_mchange` attribute decide.
    :raises NotAMemberError: if the address is not a member of the
        mailing list.
    """
    if userack is None:
        userack = mlist.send_goodbye_msg
    if admin_notif is None:
        admin_notif = mlist.admin_notify_mchanges
    # Delete a member, for which we know the approval has been made.
    member = mlist.members.get_member(email)
    if member is None:
        raise NotAMemberError(mlist, email)
    language = member.preferred_language
    member.unsubscribe()
    # And send an acknowledgement to the user...
    if userack:
        send_goodbye_message(mlist, email, language)
    # ...and to the administrator.
    if admin_notif:
        user = getUtility(IUserManager).get_user(email)
        display_name = user.display_name
        subject = _('$mlist.display_name unsubscription notification')
        text = make('adminunsubscribeack.txt',
                    mailing_list=mlist,
                    listname=mlist.display_name,
                    member=formataddr((display_name, email)),
                    )
        msg = OwnerNotification(mlist, subject, text,
                                roster=mlist.administrators)
        msg.send(mlist)
