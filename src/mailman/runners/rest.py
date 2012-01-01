# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""Start the administrative HTTP server."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'RESTRunner',
    ]


import sys
import errno
import select
import signal
import logging

from mailman.core.runner import Runner
from mailman.rest.wsgiapp import make_server


log = logging.getLogger('mailman.http')



class RESTRunner(Runner):
    intercept_signals = False

    def run(self):
        log.info('Starting REST server')
        # Handle SIGTERM the same way as SIGINT.
        def stop_server(signum, frame):
            log.info('REST server shutdown')
            sys.exit(signal.SIGTERM)
        signal.signal(signal.SIGTERM, stop_server)
        try:
            make_server().serve_forever()
        except KeyboardInterrupt:
            log.info('REST server interrupted')
            sys.exit(signal.SIGINT)
        except select.error as (errcode, message):
            if errcode == errno.EINTR:
                log.info('REST server exiting')
                sys.exit(errno.EINTR)
            raise
        except:
            raise
