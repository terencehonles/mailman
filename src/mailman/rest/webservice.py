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
    'make_server',
    ]


import logging

# Don't use wsgiref.simple_server.make_server() because we need to override
# BaseHTTPRequestHandler.log_message() so that logging output will go to the
# proper Mailman logger instead of stderr, as is the default.
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler

from lazr.restful.simple import Request
from zope.component import getUtility
from zope.interface import implements
from zope.publisher.publish import publish

from mailman.config import config
from mailman.core.system import system
from mailman.interfaces.domain import IDomainCollection, IDomainManager
from mailman.interfaces.listmanager import IListManager
from mailman.interfaces.rest import IResolvePathNames
from mailman.rest.publication import AdminWebServicePublication

log = logging.getLogger('mailman.http')



class AdminWebServiceApplication:
    """A WSGI application for the admin REST interface."""

    implements(IResolvePathNames)

    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response

    def __iter__(self):
        environ = self.environ
        # Create the request based on the HTTP method used.
        method = environ.get('REQUEST_METHOD', 'GET').upper()
        request = Request(environ['wsgi.input'], environ)
        request.setPublication(AdminWebServicePublication(self))
        # Support post-mortem debugging.
        handle_errors = environ.get('wsgi.handleErrors', True)
        # The request returned by the publisher may in fact be different than
        # the one passed in.
        request = publish(request, handle_errors=handle_errors)
        # Start the WSGI server response.
        response = request.response
        self.start_response(response.getStatusString(), response.getHeaders())
        # Return the result body iterable.
        return iter(response.consumeBodyIter())

    def get(self, name):
        """Maps root names to resources."""
        top_level = dict(
            system=system,
            domains=IDomainCollection(IDomainManager(config)),
            lists=getUtility(IListManager),
            )
        next_step = top_level.get(name)
        log.debug('Top level name: %s -> %s', name, next_step)
        return next_step



class AdminWebServiceWSGIRequestHandler(WSGIRequestHandler):
    """Handler class which just logs output to the right place."""

    def log_message(self, format, *args):
        """See `BaseHTTPRequestHandler`."""
        log.info('%s - - %s', self.address_string(), format % args)


def make_server():
    """Create the WSGI admin REST server."""
    host = config.webservice.hostname
    port = int(config.webservice.port)
    server = WSGIServer((host, port), AdminWebServiceWSGIRequestHandler)
    server.set_app(AdminWebServiceApplication)
    return server
