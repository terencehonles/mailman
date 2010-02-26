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

"""Web service helpers."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ContainerMixin',
    'etag',
    'path_to',
    ]


import json
import hashlib

from lazr.config import as_boolean
from mailman.config import config



def path_to(resource):
    """Return the url path to a resource.

    :param resource: The canonical path to the resource, relative to the
        system base URI.
    :type resource: string
    :return: The full path to the resource.
    :rtype: bytes
    """
    return b'{0}://{1}:{2}/{3}/{4}'.format(
        ('https' if as_boolean(config.webservice.use_https) else 'http'),
        config.webservice.hostname,
        config.webservice.port,
        config.webservice.api_version,
        (resource[1:] if resource.startswith('/') else resource),
        )



def etag(resource):
    """Calculate the etag and return a JSON representation.

    The input is a dictionary representing the resource.  This dictionary must
    not contain an `http_etag` key.  This function calculates the etag by
    using the sha1 hexdigest of the repr of the dictionary.  It then inserts
    this value under the `http_etag` key, and returns the JSON representation
    of the modified dictionary.

    :param resource: The original resource representation.
    :type resource: dictionary
    :return: JSON representation of the modified dictionary.
    :rtype string
    """
    assert 'http_etag' not in resource, 'Resource already etagged'
    etag = hashlib.sha1(repr(resource)).hexdigest()
    resource['http_etag'] = '"{0}"'.format(etag)
    return json.dumps(resource)



class CollectionMixin:
    """Mixin class for common collection-ish things."""

    def _resource_as_dict(self, resource):
        """Return the dictionary representation of a resource.

        This must be implemented by subclasses.

        :param resource: The resource object.
        :type resource: object
        :return: The representation of the resource.
        :rtype: dict
        """
        raise NotImplementedError

    def _resource_as_json(self, resource):
        """Return the JSON formatted representation of the resource."""
        return etag(self._resource_as_dict(resource))

    def _get_collection(self, request):
        """Return the collection as a concrete list.

        This must be implemented by subclasses.

        :param request: A restish request.
        :return: The collection
        :rtype: list
        """
        raise NotImplementedError

    def _make_collection(self, request):
        """Provide the collection to restish."""
        collection = self._get_collection(request)
        if len(collection) == 0:
            return dict(start=0, total_size=0)
        else:
            entries = [self._resource_as_dict(resource)
                       for resource in collection]
            # Tag the resources but use the dictionaries.
            [etag(resource) for resource in entries]
            # Create the collection resource
            return dict(
                start=0,
                total_size=len(collection),
                entries=entries,
                )
