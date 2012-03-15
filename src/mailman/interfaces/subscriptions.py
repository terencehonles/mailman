# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""Membership interface for REST."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ISubscriptionService',
    ]


from zope.interface import Interface

from mailman.interfaces.errors import MailmanError
from mailman.interfaces.member import DeliveryMode, MemberRole



class MissingUserError(MailmanError):
    """A an invalid user id was given."""

    def __init__(self, user_id):
        super(MissingUserError, self).__init__()
        self.user_id = user_id

    def __str__(self):
        return self.user_id



class ISubscriptionService(Interface):
    """General Subscription services."""

    def get_members():
        """Return a sequence of all members of all mailing lists.

        The members are sorted first by fully-qualified mailing list name,
        then by subscribed email address, then by role.  Because the user may
        be a member of the list under multiple roles (e.g. as an owner and as
        a digest member), the member can appear multiple times in this list.
        Roles are sorted by: owner, moderator, member.

        :return: The list of all members.
        :rtype: list of `IMember`
        """

    def get_member(member_id):
        """Return a member record matching the member id.

        :param member_id: A member id.
        :type member_id: int
        :return: The matching member, or None if no matching member is found.
        :rtype: `IMember`
        """

    def find_members(subscriber=None, fqdn_listname=None, role=None):
        """Search for and return a specific member.

        The members are sorted first by fully-qualified mailing list name,
        then by subscribed email address, then by role.  Because the user may
        be a member of the list under multiple roles (e.g. as an owner and as
        a digest member), the member can appear multiple times in this list.

        :param subscriber: The email address or user id of the user getting
            subscribed.
        :type subscriber: string or int
        :param fqdn_listname: The posting address of the mailing list to
            search for the subscriber's memberships on.
        :type fqdn_listname: string
        :param role: The member role.
        :type role: `MemberRole`
        :return: The list of all memberships, which may be empty.
        :rtype: list of `IMember`
        """

    def __iter__():
        """See `get_members()`."""

    def join(fqdn_listname, subscriber, display_name=None,
             delivery_mode=DeliveryMode.regular, 
             role=MemberRole.member):
        """Subscribe to a mailing list.

        A user for the address is created if it is not yet known to Mailman,
        however newly registered addresses will not yet be validated.  No
        confirmation message will be sent to the address, and the approval of
        the subscription request is still dependent on the policy of the
        mailing list.

        :param fqdn_listname: The posting address of the mailing list to
            subscribe the user to.
        :type fqdn_listname: string
        :param subscriber: The email address or user id of the user getting
            subscribed.
        :type subscriber: string or int
        :param display_name: The name of the user.  This is only used if a new
            user is created, and it defaults to the local part of the email
            address if not given.
        :type display_name: string
        :param delivery_mode: The delivery mode for this subscription.  This
            can be one of the enum values of `DeliveryMode`.  If not given,
            regular delivery is assumed.
        :type delivery_mode: string
        :param role: The membership role for this subscription.
        :type role: `MemberRole`
        :return: The just created member.
        :rtype: `IMember`
        :raises AlreadySubscribedError: if the user is already subscribed to
            the mailing list.
        :raises InvalidEmailAddressError: if the email address is not valid.
        :raises MembershipIsBannedError: if the membership is not allowed.
        :raises MissingUserError: when a bogus user id is given.
        :raises NoSuchListError: if the named mailing list does not exist.
        :raises ValueError: when `delivery_mode` is invalid.
        """

    def leave(fqdn_listname, email):
        """Unsubscribe from a mailing list.

        :param fqdn_listname: The posting address of the mailing list to
            unsubscribe the user from.
        :type fqdn_listname: string
        :param email: The email address of the user getting unsubscribed.
        :type email: string
        :raises InvalidEmailAddressError: if the email address is not valid.
        :raises NoSuchListError: if the named mailing list does not exist.
        :raises NotAMemberError: if the given address is not a member of the
            mailing list.
        """
