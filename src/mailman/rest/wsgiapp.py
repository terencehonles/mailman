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

"""Basic WSGI Application object for REST server."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'make_application',
    'make_server',
    ]


import logging

from restish.app import RestishApp
from wsgiref.simple_server import WSGIRequestHandler
from wsgiref.simple_server import make_server as wsgi_server

from mailman.config import config
from mailman.rest.root import Root


log = logging.getLogger('mailman.http')



class AdminWebServiceWSGIRequestHandler(WSGIRequestHandler):
    """Handler class which just logs output to the right place."""

    def log_message(self, format, *args):
        """See `BaseHTTPRequestHandler`."""
        log.info('%s - - %s', self.address_string(), format % args)


class AdminWebServiceApplication(RestishApp):
    """Connect the restish WSGI application to Mailman's database."""

    def __call__(self, environ, start_response):
        """See `RestishApp`."""
        try:
            response = super(AdminWebServiceApplication, self).__call__(
                environ, start_response)
        except:
            config.db.abort()
            raise
        else:
            config.db.commit()
            return response



def make_application():
    """Create the WSGI application.

    Use this if you want to integrate Mailman's REST server with your own WSGI
    server.
    """
    return AdminWebServiceApplication(Root())


def make_server():
    """Create the Mailman REST server.

    Use this if you just want to run Mailman's wsgiref-based REST server.
    """
    host = config.webservice.hostname
    port = int(config.webservice.port)
    server = wsgi_server(
        host, port, make_application(),
        handler_class=AdminWebServiceWSGIRequestHandler)
    return server
