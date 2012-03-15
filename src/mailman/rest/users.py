# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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


from flufl.password import lookup, make_secret, generate
from restish import http, resource
from uuid import UUID
from zope.component import getUtility

from mailman.config import config
from mailman.interfaces.address import ExistingAddressError
from mailman.interfaces.usermanager import IUserManager
from mailman.rest.addresses import UserAddresses
from mailman.rest.helpers import CollectionMixin, etag, no_content, path_to
from mailman.rest.preferences import Preferences
from mailman.rest.validator import Validator



class _UserBase(resource.Resource, CollectionMixin):
    """Shared base class for user representations."""

    def _resource_as_dict(self, user):
        """See `CollectionMixin`."""
        # The canonical URL for a user is their unique user id, although we
        # can always look up a user based on any registered and validated
        # email address associated with their account.  The user id is a UUID,
        # but we serialize its integer equivalent.
        user_id = user.user_id.int
        resource = dict(
            user_id=user_id,
            created_on=user.created_on,
            self_link=path_to('users/{0}'.format(user_id)),
            )
        # Add the password attribute, only if the user has a password.  Same
        # with the real name.  These could be None or the empty string.
        if user.password:
            resource['password'] = user.password
        if user.display_name:
            resource['display_name'] = user.display_name
        return resource

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

    @resource.POST()
    def create(self, request):
        """Create a new user."""
        try:
            validator = Validator(email=unicode,
                                  display_name=unicode,
                                  password=unicode,
                                  _optional=('display_name', 'password'))
            arguments = validator(request)
        except ValueError as error:
            return http.bad_request([], str(error))
        # We can't pass the 'password' argument to the user creation method,
        # so strip that out (if it exists), then create the user, adding the
        # password after the fact if successful.
        password = arguments.pop('password', None)
        try:
            user = getUtility(IUserManager).create_user(**arguments)
        except ExistingAddressError as error:
            return http.bad_request([], b'Address already exists {0}'.format(
                error.email))
        if password is None:
            # This will have to be reset since it cannot be retrieved.
            password = generate(int(config.passwords.password_length))
        scheme = lookup(config.passwords.password_scheme.upper())
        user.password = make_secret(password, scheme)
        location = path_to('users/{0}'.format(user.user_id.int))
        return http.created(location, [], None)



class AUser(_UserBase):
    """A user."""

    def __init__(self, user_identifier):
        """Get a user by various type of identifiers.

        :param user_identifier: The identifier used to retrieve the user.  The
            identifier may either be an integer user-id, or an email address
            controlled by the user.  The type of identifier is auto-detected
            by looking for an `@` symbol, in which case it's taken as an email
            address, otherwise it's assumed to be an integer.
        :type user_identifier: string
        """
        user_manager = getUtility(IUserManager)
        if '@' in user_identifier:
            self._user = user_manager.get_user(user_identifier)
        else:
            # The identifier is the string representation of an integer that
            # must be converted to a UUID.
            try:
                user_id = UUID(int=int(user_identifier))
            except ValueError:
                self._user = None
            else:
                self._user = user_manager.get_user_by_id(user_id)

    @resource.GET()
    def user(self, request):
        """Return a single user end-point."""
        if self._user is None:
            return http.not_found()
        return http.ok([], self._resource_as_json(self._user))

    @resource.child()
    def addresses(self, request, segments):
        """/users/<uid>/addresses"""
        return UserAddresses(self._user)

    @resource.DELETE()
    def delete_user(self, request):
        """Delete the named user."""
        if self._user is None:
            return http.not_found()
        getUtility(IUserManager).delete_user(self._user)
        return no_content()

    @resource.child()
    def preferences(self, request, segments):
        """/addresses/<email>/preferences"""
        if len(segments) != 0:
            return http.bad_request()
        if self._user is None:
            return http.not_found()
        child = Preferences(
            self._user.preferences,
            'users/{0}'.format(self._user.user_id.int))
        return child, []
