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

"""The root of the REST API."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Root',
    ]


from restish import http, resource, guard
from base64 import b64decode

from mailman.config import config
from mailman.core.system import system
from mailman.rest.domains import ADomain, AllDomains
from mailman.rest.helpers import etag, path_to
from mailman.rest.lists import AList, AllLists
from mailman.rest.members import AllMembers



def webservice_auth_checker(request, obj):
    if "HTTP_AUTHORIZATION" in request.environ and request.environ["HTTP_AUTHORIZATION"].startswith("Basic "):
        credentials = b64decode(request.environ["HTTP_AUTHORIZATION"][6:])
        username, password = credentials.split(":", 1)

        if username != config.webservice.admin_user or password != config.webservice.admin_pass:
            raise guard.GuardError(str("User is not authorized for the REST api."))
    else:
        raise guard.GuardError(str("The REST api requires authentication."))

class Root(resource.Resource):
    """The RESTful root resource.

    At the root of the tree are the API version numbers.  Everything else
    lives underneath those.  Currently there is only one API version number,
    and we start at 3.0 to match the Mailman version number.  That may not
    always be the case though.
    """

    @resource.child(config.webservice.api_version)
    @guard.guard(webservice_auth_checker)
    def api_version(self, request, segments):
        return TopLevel()

class TopLevel(resource.Resource):
    """Top level collections and entries."""

    @resource.child()
    def system(self, request, segments):
        """/<api>/system"""
        resource = dict(
            mailman_version=system.mailman_version,
            python_version=system.python_version,
            self_link=path_to('system'),
            )
        return http.ok([], etag(resource))

    @resource.child()
    def domains(self, request, segments):
        """/<api>/domains
           /<api>/domains/<domain>
        """
        if len(segments) == 0:
            return AllDomains()
        elif len(segments) == 1:
            return ADomain(segments[0]), []
        else:
            return http.bad_request()

    @resource.child()
    def lists(self, request, segments):
        """/<api>/lists
           /<api>/lists/<list>
           /<api>/lists/<list>/...
        """
        if len(segments) == 0:
            return AllLists()
        else:
            list_name = segments.pop(0)
            return AList(list_name), segments

    @resource.child()
    def members(self, request, segments):
        """/<api>/members"""
        if len(segments) == 0:
            return AllMembers()
        return http.bad_request()
