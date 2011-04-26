# Copyright (C) 2010-2011 by the Free Software Foundation, Inc.
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
    'MemberCollection',
    ]


from restish import http, resource
from zope.component import getUtility

from mailman.app.membership import delete_member
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.listmanager import IListManager, NoSuchListError
from mailman.interfaces.member import (
    AlreadySubscribedError, DeliveryMode, MemberRole, MembershipError,
    NotAMemberError)
from mailman.interfaces.membership import ISubscriptionService
from mailman.interfaces.user import UnverifiedAddressError
from mailman.interfaces.usermanager import IUserManager
from mailman.rest.helpers import (
    CollectionMixin, PATCH, etag, no_content, path_to)
from mailman.rest.validator import Validator, enum_validator



class _MemberBase(resource.Resource, CollectionMixin):
    """Shared base class for member representations."""

    def _resource_as_dict(self, member):
        """See `CollectionMixin`."""
        enum, dot, role = str(member.role).partition('.')
        return dict(
            fqdn_listname=member.mailing_list,
            address=member.address.email,
            role=role,
            user=path_to('users/{0}'.format(member.user.user_id)),
            self_link=path_to('members/{0}'.format(member.member_id)),
            )

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(ISubscriptionService))



class AMember(_MemberBase):
    """A member."""

    def __init__(self, member_id):
        self._member_id = member_id
        self._member = getUtility(ISubscriptionService).get_member(member_id)

    @resource.GET()
    def member(self, request):
        """Return a single member end-point."""
        return http.ok([], self._resource_as_json(self._member))

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
        # Currently, only the `address` parameter can be patched.
        values = Validator(address=unicode)(request)
        assert len(values) == 1, 'Unexpected values'
        email = values['address']
        address = getUtility(IUserManager).get_address(email)
        if address is None:
            return http.bad_request([], b'Address not registered')
        try:
            self._member.address = address
        except (MembershipError, UnverifiedAddressError) as error:
            return http.bad_request([], str(error))
        return no_content()



class AllMembers(_MemberBase):
    """The members."""

    @resource.POST()
    def create(self, request):
        """Create a new member."""
        service = getUtility(ISubscriptionService)
        try:
            validator = Validator(fqdn_listname=unicode,
                                  subscriber=unicode,
                                  real_name=unicode,
                                  delivery_mode=enum_validator(DeliveryMode),
                                  _optional=('delivery_mode', 'real_name'))
            member = service.join(**validator(request))
        except AlreadySubscribedError:
            return http.conflict([], b'Member already subscribed')
        except NoSuchListError:
            return http.bad_request([], b'No such list')
        except InvalidEmailAddressError:
            return http.bad_request([], b'Invalid email address')
        except ValueError as error:
            return http.bad_request([], str(error))
        location = path_to('members/{0}'.format(member.member_id))
        # Include no extra headers or body.
        return http.created(location, [], None)

    @resource.GET()
    def container(self, request):
        """/members"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))



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
