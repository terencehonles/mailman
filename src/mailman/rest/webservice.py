# Copyright (C) 2009 by the Free Software Foundation, Inc.
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

"""Module stuff."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AdminWebServiceApplication',
    'AdminWebServiceRequest',
    'start',
    ]


from wsgiref.simple_server import make_server

from lazr.restful.publisher import WebServiceRequestTraversal
from pkg_resources import resource_string
from zope.configuration import xmlconfig
from zope.interface import implements
from zope.publisher.browser import BrowserRequest
from zope.publisher.publish import publish

from mailman.core.system import system
from mailman.interfaces.rest import IResolvePathNames
from mailman.rest.publication import AdminWebServicePublication



class AdminWebServiceRequest(WebServiceRequestTraversal, BrowserRequest):
    """A request for the admin REST interface."""


class AdminWebServiceApplication:
    """A WSGI application for the admin REST interface."""

    implements(IResolvePathNames)

    def __init__(self, environ, start_response):
        # Create the request based on the HTTP method used.
        method = environ.get('REQUEST_METHOD', 'GET').upper()
        request = AdminWebServiceRequest(environ['wsgi.input'], environ)
        request.setPublication(AdminWebServicePublication(self))
        # Support post-mortem debugging.
        handle_errors = environ.get('wsgi.handleErrors', True)
        # The request returned by the publisher may in fact be different than
        # the one passed in.
        request = publish(request, handle_errors=handle_errors)
        # Start the WSGI server response.
        response = request.response
        start_response(response.getStatusString(), response.getHeaders())
        # Return the result body iterable.
        return response.consumeBodyIter()

    def get(self, name):
        """Maps root names to resources."""
        top_level = dict(
            sys=system,
            )
        return top_level.get(name)



def start():
    """Start the WSGI admin REST service."""
    zcml = resource_string('mailman.rest', 'configure.zcml')
    xmlconfig.string(zcml)
    server = make_server('', 8001, AdminWebServiceApplication)
    return server


if __name__ == '__main__':
    start().serve_forever()
