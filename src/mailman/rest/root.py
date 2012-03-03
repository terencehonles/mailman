# Copyright (C) 2010-2012 by the Free Software Foundation, Inc.
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


from base64 import b64decode
from restish import guard, http, resource
from zope.component import getUtility

from mailman.config import config
from mailman.core.constants import system_preferences
from mailman.core.system import system
from mailman.interfaces.listmanager import IListManager
from mailman.rest.addresses import AllAddresses, AnAddress
from mailman.rest.domains import ADomain, AllDomains
from mailman.rest.helpers import etag, path_to
from mailman.rest.lists import AList, AllLists
from mailman.rest.members import AMember, AllMembers, FindMembers
from mailman.rest.preferences import ReadOnlyPreferences
from mailman.rest.templates import TemplateFinder
from mailman.rest.users import AUser, AllUsers



def webservice_auth_checker(request, obj):
    auth = request.environ.get('HTTP_AUTHORIZATION', '')
    if auth.startswith('Basic '):
        credentials = b64decode(auth[6:])
        username, password = credentials.split(':', 1)
        if (username != config.webservice.admin_user or
            password != config.webservice.admin_pass):
            # Not authorized.
            raise guard.GuardError(b'User is not authorized for the REST API')
    else:
        raise guard.GuardError(b'The REST API requires authentication')


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
        if len(segments) == 0:
            resource = dict(
                mailman_version=system.mailman_version,
                python_version=system.python_version,
                self_link=path_to('system'),
                )
        elif len(segments) > 1:
            return http.bad_request()
        elif segments[0] == 'preferences':
            return ReadOnlyPreferences(system_preferences, 'system'), []
        else:
            return http.bad_request()
        return http.ok([], etag(resource))

    @resource.child()
    def addresses(self, request, segments):
        """/<api>/addresses
           /<api>/addresses/<email>
        """
        if len(segments) == 0:
            return AllAddresses()
        else:
            email = segments.pop(0)
            return AnAddress(email), segments

    @resource.child()
    def domains(self, request, segments):
        """/<api>/domains
           /<api>/domains/<domain>
        """
        if len(segments) == 0:
            return AllDomains()
        else:
            domain = segments.pop(0)
            return ADomain(domain), segments

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
        # Either the next segment is the string "find" or a member id.  They
        # cannot collide.
        segment = segments.pop(0)
        if segment == 'find':
            return FindMembers(), segments
        else:
            return AMember(segment), segments

    @resource.child()
    def users(self, request, segments):
        """/<api>/users"""
        if len(segments) == 0:
            return AllUsers()
        else:
            user_id = segments.pop(0)
            return AUser(user_id), segments

    @resource.child()
    def templates(self, request, segments):
        """/<api>/templates/<fqdn_listname>/<template>/[<language>]

        Use content negotiation to request language and suffix (content-type).
        """
        if len(segments) == 3:
            fqdn_listname, template, language = segments
        elif len(segments) == 2:
            fqdn_listname, template = segments
            language = 'en'
        else:
            return http.bad_request()
        mlist = getUtility(IListManager).get(fqdn_listname)
        if mlist is None:
            return http.not_found()
        # XXX dig out content-type from request
        content_type = None
        return TemplateFinder(
            fqdn_listname, template, language, content_type)
