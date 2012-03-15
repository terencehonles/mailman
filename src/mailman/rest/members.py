# Copyright (C) 2010-2012 by the Free Software Foundation, Inc.
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

"""REST for members."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AMember',
    'AllMembers',
    'FindMembers',
    'MemberCollection',
    ]


from uuid import UUID
from operator import attrgetter
from restish import http, resource
from zope.component import getUtility

from mailman.app.membership import delete_member
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.listmanager import IListManager, NoSuchListError
from mailman.interfaces.member import (
    AlreadySubscribedError, DeliveryMode, MemberRole, MembershipError,
    NotAMemberError)
from mailman.interfaces.subscriptions import ISubscriptionService
from mailman.interfaces.user import UnverifiedAddressError
from mailman.interfaces.usermanager import IUserManager
from mailman.rest.helpers import (
    CollectionMixin, PATCH, etag, no_content, path_to)
from mailman.rest.preferences import Preferences, ReadOnlyPreferences
from mailman.rest.validator import (
    Validator, enum_validator, subscriber_validator)



class _MemberBase(resource.Resource, CollectionMixin):
    """Shared base class for member representations."""

    def _resource_as_dict(self, member):
        """See `CollectionMixin`."""
        enum, dot, role = str(member.role).partition('.')
        # Both the user_id and the member_id are UUIDs.  We need to use the
        # integer equivalent in the URL.
        user_id = member.user.user_id.int
        member_id = member.member_id.int
        return dict(
            fqdn_listname=member.mailing_list,
            address=member.address.email,
            role=role,
            user=path_to('users/{0}'.format(user_id)),
            self_link=path_to('members/{0}'.format(member_id)),
            delivery_mode=member.delivery_mode,
            )

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(ISubscriptionService))



class MemberCollection(_MemberBase):
    """Abstract class for supporting submemberships.

    This is used for example to return a resource representing all the
    memberships of a mailing list, or all memberships for a specific email
    address.
    """
    def _get_collection(self, request):
        """See `CollectionMixin`."""
        raise NotImplementedError

    @resource.GET()
    def container(self, request):
        """roster/[members|owners|moderators]"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))



class AMember(_MemberBase):
    """A member."""

    def __init__(self, member_id_string):
        # REST gives us the member id as the string of an int; we have to
        # convert it to a UUID.
        try:
            member_id = UUID(int=int(member_id_string))
        except ValueError:
            # The string argument could not be converted to an integer.
            self._member = None
        else:
            service = getUtility(ISubscriptionService)
            self._member = service.get_member(member_id)

    @resource.GET()
    def member(self, request):
        """Return a single member end-point."""
        if self._member is None:
            return http.not_found()
        return http.ok([], self._resource_as_json(self._member))

    @resource.child()
    def preferences(self, request, segments):
        """/members/<id>/preferences"""
        if len(segments) != 0:
            return http.bad_request()
        if self._member is None:
            return http.not_found()
        child = Preferences(
            self._member.preferences,
            'members/{0}'.format(self._member.member_id.int))
        return child, []

    @resource.child()
    def all(self, request, segments):
        """/members/<id>/all/preferences"""
        if len(segments) == 0:
            return http.not_found()
        if self._member is None:
            return http.not_found()
        child = ReadOnlyPreferences(
            self._member,
            'members/{0}/all'.format(self._member.member_id.int))
        return child, []

    @resource.DELETE()
    def delete(self, request):
        """Delete the member (i.e. unsubscribe)."""
        # Leaving a list is a bit different than deleting a moderator or
        # owner.  Handle the former case first.  For now too, we will not send
        # an admin or user notification.
        if self._member is None:
            return http.not_found()
        mlist = getUtility(IListManager).get(self._member.mailing_list)
        if self._member.role is MemberRole.member:
            try:
                delete_member(mlist, self._member.address.email, False, False)
            except NotAMemberError:
                return http.not_found()
        else:
            self._member.unsubscribe()
        return no_content()

    @PATCH()
    def patch_membership(self, request):
        """Patch the membership.

        This is how subscription changes are done.
        """
        if self._member is None:
            return http.not_found()
        try:
            values = Validator(
                address=unicode,
                delivery_mode=enum_validator(DeliveryMode),
                _optional=('address', 'delivery_mode'))(request)
        except ValueError as error:
            return http.bad_request([], str(error))
        if 'address' in values:
            email = values['address']
            address = getUtility(IUserManager).get_address(email)
            if address is None:
                return http.bad_request([], b'Address not registered')
            try:
                self._member.address = address
            except (MembershipError, UnverifiedAddressError) as error:
                return http.bad_request([], str(error))
        if 'delivery_mode' in values:
            self._member.preferences.delivery_mode = values['delivery_mode']
        return no_content()



class AllMembers(_MemberBase):
    """The members."""

    @resource.POST()
    def create(self, request):
        """Create a new member."""
        service = getUtility(ISubscriptionService)
        try:
            validator = Validator(
                fqdn_listname=unicode,
                subscriber=subscriber_validator,
                display_name=unicode,
                delivery_mode=enum_validator(DeliveryMode),
                role=enum_validator(MemberRole),
                _optional=('delivery_mode', 'display_name', 'role'))
            member = service.join(**validator(request))
        except AlreadySubscribedError:
            return http.conflict([], b'Member already subscribed')
        except NoSuchListError:
            return http.bad_request([], b'No such list')
        except InvalidEmailAddressError:
            return http.bad_request([], b'Invalid email address')
        except ValueError as error:
            return http.bad_request([], str(error))
        # The member_id are UUIDs.  We need to use the integer equivalent in
        # the URL.
        member_id = member.member_id.int
        location = path_to('members/{0}'.format(member_id))
        # Include no extra headers or body.
        return http.created(location, [], None)

    @resource.GET()
    def container(self, request):
        """/members"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))



class _FoundMembers(MemberCollection):
    """The found members collection."""

    def __init__(self, members):
        super(_FoundMembers, self).__init__()
        self._members = members

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        address_of_member = attrgetter('address.email')
        return list(sorted(self._members, key=address_of_member))


class FindMembers(_MemberBase):
    """/members/find"""

    @resource.POST()
    def find(self, request):
        """Find a member"""
        service = getUtility(ISubscriptionService)
        validator = Validator(
            fqdn_listname=unicode,
            subscriber=unicode,
            role=enum_validator(MemberRole),
            _optional=('fqdn_listname', 'subscriber', 'role'))
        members = service.find_members(**validator(request))
        # We can't just return the _FoundMembers instance, because
        # CollectionMixins have only a GET method, which is incompatible with
        # this POSTed resource.  IOW, without doing this here, restish would
        # throw a 405 Method Not Allowed.
        resource = _FoundMembers(members)._make_collection(request)
        return http.ok([], etag(resource))
