# Copyright (C) 2006-2009 by the Free Software Foundation, Inc.
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

"""Mailman HTTP runner (server)."""

import sys
import signal
import logging

from cStringIO import StringIO
from wsgiref.simple_server import make_server, WSGIRequestHandler

from mailman.Cgi.wsgi_app import mailman_app
from mailman.config import config
from mailman.queue import Runner

hlog = logging.getLogger('mailman.http')
qlog = logging.getLogger('mailman.qrunner')



class HTTPRunner(Runner):
    def __init__(self, slice=None, numslices=1):
        pass

    def _clean_up(self):
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
hlog.info('HTTPRunner listening on %s:%s', config.HTTP_HOST, config.HTTP_PORT)
try:
    server.serve_forever()
except KeyboardInterrupt:
    qlog.exception('HTTPRunner qrunner exiting.')
    sys.exit(signal.SIGTERM)
except:
    qlog.exception('HTTPRunner qrunner exiting.')
    raise
