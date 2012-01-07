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

"""Preferences."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ReadOnlyPreferences',
    'Preferences',
    ]


from lazr.config import as_boolean
from restish import http, resource

from mailman.interfaces.member import DeliveryMode, DeliveryStatus
from mailman.rest.helpers import PATCH, etag, no_content, path_to
from mailman.rest.validator import (
    Validator, enum_validator, language_validator)


PREFERENCES = (
    'acknowledge_posts',
    'delivery_mode',
    'delivery_status',
    'hide_address',
    'preferred_language',
    'receive_list_copy',
    'receive_own_postings',
    )



class ReadOnlyPreferences(resource.Resource):
    """.../<object>/preferences"""

    def __init__(self, parent, base_url):
        self._parent = parent
        self._base_url = base_url

    @resource.GET()
    def preferences(self, segments):
        resource = dict()
        for attr in PREFERENCES:
            # Handle this one specially.
            if attr == 'preferred_language':
                continue
            value = getattr(self._parent, attr, None)
            if value is not None:
                resource[attr] = value
        # Add the preferred language, if it's not missing.
        preferred_language = self._parent.preferred_language
        if preferred_language is not None:
            resource['preferred_language'] = preferred_language.code
        # Add the self link.
        resource['self_link'] = path_to(
            '{0}/preferences'.format(self._base_url))
        return http.ok([], etag(resource))
    


class Preferences(ReadOnlyPreferences):
    """Preferences which can be changed."""

    def patch_put(self, request, is_optional):
        if self._parent is None:
            return http.not_found()
        kws = dict(
            acknowledge_posts=as_boolean,
            delivery_mode=enum_validator(DeliveryMode),
            delivery_status=enum_validator(DeliveryStatus),
            preferred_language=language_validator,
            receive_list_copy=as_boolean,
            receive_own_postings=as_boolean,
            )
        if is_optional:
            # For a PUT, all attributes are optional.
            kws['_optional'] = kws.keys()
        try:
            values = Validator(**kws)(request)
        except ValueError as error:
            return http.bad_request([], str(error))
        for key, value in values.items():
            setattr(self._parent, key, value)
        return no_content()

    @PATCH()
    def patch_preferences(self, request):
        """Patch the preferences."""
        return self.patch_put(request, is_optional=True)

    @resource.PUT()
    def put_preferences(self, request):
        """Change all preferences."""
        return self.patch_put(request, is_optional=False)

    @resource.DELETE()
    def delete_preferences(self, request):
        """Delete all preferences."""
        for attr in PREFERENCES:
            if hasattr(self._parent, attr):
                setattr(self._parent, attr, None)
        return no_content()
