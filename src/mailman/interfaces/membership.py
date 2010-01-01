# Copyright (C) 2009-2010 by the Free Software Foundation, Inc.
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
    'SubscriptionService',
    ]


from lazr.restful.declarations import (
    collection_default_content, export_as_webservice_collection,
    export_write_operation, operation_parameters)
from zope.interface import Interface
from zope.schema import TextLine

from mailman.core.i18n import _
from mailman.interfaces.member import IMember



class ISubscriptionService(Interface):
    """Subscription services for the REST API."""

    export_as_webservice_collection(IMember)

    @collection_default_content()
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

    @operation_parameters(
        fqdn_listname=TextLine(),
        address=TextLine(),
        real_name=TextLine(),
        delivery_mode=TextLine(),
        )
    @export_write_operation()
    def join(fqdn_listname, address, real_name=None, delivery_mode=None):
        """Subscribe to a mailing list.

        A user for the address is created if it is not yet known to Mailman,
        however newly registered addresses will not yet be validated.  No
        confirmation message will be sent to the address, and the approval of
        the subscription request is still dependent on the policy of the
        mailing list.

        :param fqdn_listname: The posting address of the mailing list to
            subscribe the user to.
        :type fqdn_listname: string
        :param address: The address of the user getting subscribed.
        :type address: string
        :param real_name: The name of the user.  This is only used if a new
            user is created, and it defaults to the local part of the email
            address if not given.
        :type real_name: string
        :param delivery_mode: The delivery mode for this subscription.  This
            can be one of the enum values of `DeliveryMode`.  If not given,
            regular delivery is assumed.
        :type delivery_mode: string
        :return: The just created member.
        :rtype: `IMember`
        :raises AlreadySubscribedError: if the user is already subscribed to
            the mailing list.
        :raises InvalidEmailAddressError: if the email address is not valid.
        :raises MembershipIsBannedError: if the membership is not allowed.
        :raises NoSuchListError: if the named mailing list does not exist.
        :raises ValueError: when `delivery_mode` is invalid.
        """

    @operation_parameters(
        fqdn_listname=TextLine(),
        address=TextLine(),
        )
    @export_write_operation()
    def leave(fqdn_listname, address):
        """Unsubscribe from a mailing list.

        :param fqdn_listname: The posting address of the mailing list to
            subscribe the user to.
        :type fqdn_listname: string
        :param address: The address of the user getting subscribed.
        :type address: string
        :raises InvalidEmailAddressError: if the email address is not valid.
        :raises NoSuchListError: if the named mailing list does not exist.
        :raises NotAMemberError: if the given address is not a member of the
            mailing list.
        """
        
