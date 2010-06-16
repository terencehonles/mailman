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
    ]


from restish import http, resource
from zope.component import getUtility

from mailman.app.membership import delete_member
from mailman.interfaces.address import InvalidEmailAddressError
from mailman.interfaces.listmanager import NoSuchListError
from mailman.interfaces.member import (
    AlreadySubscribedError, DeliveryMode, MemberRole)
from mailman.interfaces.membership import ISubscriptionService
from mailman.rest.helpers import CollectionMixin, Validator, etag, path_to



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
        # XXX 2010-02-24 barry There should be a more direct way to get a
        # member out of a mailing list.
        if self._role is MemberRole.member:
            roster = self._mlist.members
        elif self._role is MemberRole.owner:
            roster = self._mlist.owners
        elif self._role is MemberRole.moderator:
            roster = self._mlist.moderators
        else:
            raise AssertionError(
                'Undefined MemberRole: {0}'.format(self._role))
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
                                  delivery_mode=unicode,
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
        # wsgiref wants headers to be bytes, not unicodes.
        location = path_to('lists/{0}/member/{1}'.format(
            member.mailing_list, member.address.address))
        # Include no extra headers or body.
        return http.created(location, [], None)

    @resource.GET()
    def container(self, request):
        """/members"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))
