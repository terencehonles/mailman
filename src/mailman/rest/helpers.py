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
    'no_content',
    'path_to',
    'restish_matcher',
    ]


import json
import hashlib

from datetime import datetime
from lazr.config import as_boolean
from restish.http import Response

from mailman.config import config


COMMASPACE = ', '



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



class ExtendedEncoder(json.JSONEncoder):
    """An extended JSON encoder which knows about other data types."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


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
    return json.dumps(resource, cls=ExtendedEncoder)



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



class Validator:
    """A validator of parameter input."""

    def __init__(self, **kws):
        if '_optional' in kws:
            self._optional = set(kws.pop('_optional'))
        else:
            self._optional = set()
        self._converters = kws.copy()

    def __call__(self, request):
        values = {}
        extras = set()
        cannot_convert = set()
        for key, value in request.POST.items():
            try:
                values[key] = self._converters[key](value)
            except KeyError:
                extras.add(key)
            except (TypeError, ValueError):
                cannot_convert.add(key)
        # Make sure there are no unexpected values.
        if len(extras) != 0:
            extras = COMMASPACE.join(sorted(extras))
            raise ValueError('Unexpected parameters: {0}'.format(extras))
        # Make sure everything could be converted.
        if len(cannot_convert) != 0:
            bad = COMMASPACE.join(sorted(cannot_convert))
            raise ValueError('Cannot convert parameters: {0}'.format(bad))
        # Make sure nothing's missing.
        value_keys = set(values)
        required_keys = set(self._converters) - self._optional
        if value_keys & required_keys != required_keys:
            missing = COMMASPACE.join(sorted(required_keys - value_keys))
            raise ValueError('Missing parameters: {0}'.format(missing))
        return values



# XXX 2010-02-24 barry Seems like contrary to the documentation, matchers
# cannot be plain functions, because matchers must have a .score attribute.
# OTOH, I think they support regexps, so that might be a better way to go.
def restish_matcher(function):
    """Decorator for restish matchers."""
    function.score = ()
    return function


# restish doesn't support HTTP response code 204.
def no_content():
    """204 No Content."""
    return Response('204 No Content', [], None)
