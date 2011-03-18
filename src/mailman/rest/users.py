# Copyright (C) 2011 by the Free Software Foundation, Inc.
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

"""REST for users."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AUser',
    'AllUsers',
    ]


from restish import http, resource
from zope.component import getUtility

from mailman.interfaces.usermanager import IUserManager
from mailman.rest.helpers import CollectionMixin, etag



class _UserBase(resource.Resource, CollectionMixin):
    """Shared base class for user representations."""

    def _resource_as_dict(self, user):
        """See `CollectionMixin`."""
        # The canonical URL for a user is their preferred email address,
        # although we can always look up a user based on any registered and
        # validated email address associated with their account.
        return dict(
            real_name=user.real_name,
            password=user.password,
            user_id=user.user_id,
            )

    def _get_collection(self, request):
        """See `CollectionMixin`."""
        return list(getUtility(IUserManager).users)



class AllUsers(_UserBase):
    """The users."""

    @resource.GET()
    def collection(self, request):
        """/users"""
        resource = self._make_collection(request)
        return http.ok([], etag(resource))



class AUser(_UserBase):
    """A user."""

    def __init__(self, user_id):
        self._user = getUtility(IUserManager).get_user_by_id(user_id)

    @resource.GET()
    def user(self, request):
        """Return a single user end-point."""
        if self._user is None:
            return http.not_found()
        return http.ok([], self._resource_as_json(self._user))
