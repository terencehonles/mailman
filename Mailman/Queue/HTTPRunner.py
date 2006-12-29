# Copyright (C) 2006 by the Free Software Foundation, Inc.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Mailman HTTP runner (server)."""

import sys
import logging

from cStringIO import StringIO
from wsgiref.simple_server import make_server, WSGIRequestHandler

from Mailman.Cgi.wsgi_app import mailman_app
from Mailman.Queue.Runner import Runner
from Mailman.configuration import config

hlog = logging.getLogger('mailman.http')
qlog = logging.getLogger('mailman.qrunner')



class HTTPRunner(Runner):
    def __init__(self, slice=None, numslices=1):
        pass

    def _cleanup(self):
        pass



class MailmanWSGIRequestHandler(WSGIRequestHandler):
    def handle(self):
        """Handle a single HTTP request with error output to elog"""
        stderr = StringIO()
        saved_stderr = sys.stderr
        sys.stderr = stderr
        try:
            WSGIRequestHandler.handle(self)
        finally:
            sys.stderr = saved_stderr
        hlog.info(stderr.getvalue().strip())



server = make_server(config.HTTP_HOST, config.HTTP_PORT,
                     mailman_app,
                     handler_class=MailmanWSGIRequestHandler)


qlog.info('HTTPRunner qrunner started.')
try:
    server.serve_forever()
except:
    qlog.exception('HTTPRunner qrunner exiting.')
    raise
