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
    'MembersOfList',
    ]


from operator import attrgetter
from restish import http, resource
from zope.component import getUtility

from mailman.app.membership import delete_member
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.listmanager import IListManager, NoSuchListError
from mailman.interfaces.member import (
    AlreadySubscribedError, DeliveryMode, MemberRole, NotAMemberError)
from mailman.interfaces.membership import ISubscriptionService
from mailman.rest.helpers import CollectionMixin, etag, path_to
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
        return http.ok([], '')



class AllMembers(_MemberBase):
    """The members."""

    @resource.POST()
    def create(self, request):
        """Create a new member."""
        service = getUtility(ISubscriptionService)
        try:
            validator = Validator(fqdn_listname=unicode,
                                  address=unicode,
                                  real_name=unicode,
                                  delivery_mode=enum_validator(DeliveryMode),
                                  _optional=('real_name', 'delivery_mode'))
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



class MembersOfList(_MemberBase):
    """The members of a mailing list."""

    def __init__(self, mailing_list, role):
        self._mlist = mailing_list
        self._role = role

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        # Overrides _MemberBase._get_collection() because we only want to
        # return the members from the requested roster.
        roster = self._mlist.get_roster(self._role)
        address_of_member = attrgetter('address.email')
        return list(sorted(roster.members, key=address_of_member))

    @resource.GET()
    def container(self, request):
        """roster/[members|owners|moderators]"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))
