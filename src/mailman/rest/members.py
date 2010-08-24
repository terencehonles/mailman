# Copyright (C) 2010 by the Free Software Foundation, Inc.
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
from urllib import quote
from zope.component import getUtility

from mailman.app.membership import delete_member
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.listmanager import NoSuchListError
from mailman.interfaces.member import (
    AlreadySubscribedError, DeliveryMode, MemberRole)
from mailman.interfaces.membership import ISubscriptionService
from mailman.rest.helpers import CollectionMixin, etag, path_to
from mailman.rest.validator import Validator, enum_validator



class _MemberBase(resource.Resource, CollectionMixin):
    """Shared base class for member representations."""

    def _resource_as_dict(self, member):
        """See `CollectionMixin`."""
        enum, dot, role = str(member.role).partition('.')
        return dict(
            self_link=path_to('lists/{0}/{1}/{2}'.format(
                member.mailing_list, role, member.address.address)),
            )

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(ISubscriptionService))


class AMember(_MemberBase):
    """A member."""

    def __init__(self, mailing_list, role, address):
        self._mlist = mailing_list
        self._role = role
        self._address = address
        roster = self._mlist.get_roster(role)
        self._member = roster.get_member(self._address)

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
        if self._role is MemberRole.member:
            delete_member(self._mlist, self._address, False, False)
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
        # wsgiref wants headers to be bytes, not unicodes.  Also, we have to
        # quote any unsafe characters in the address.  Specifically, we need
        # to quote forward slashes, but not @-signs.
        quoted_address = quote(member.address.address, safe=b'@')
        location = path_to('lists/{0}/member/{1}'.format(
            member.mailing_list, quoted_address))
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
        address_of_member = attrgetter('address.address')
        return list(sorted(roster.members, key=address_of_member))

    @resource.GET()
    def container(self, request):
        """roster/[members|owners|moderators]"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))
