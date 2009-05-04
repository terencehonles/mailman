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

"""A testable REST server."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'TestableServer',
    ]


import logging
import threading

from urllib2 import urlopen

from mailman.rest.webservice import make_server


log = logging.getLogger('mailman.http')



class TestableServer:
    """A REST server which polls for the stop action."""

    def __init__(self):
        self.server = make_server()
        self.event = threading.Event()
        self.thread = threading.Thread(target=self.loop)
        
    def start(self):
        """Start the server."""
        self.thread.start()

    def stop(self):
        """Stop the server by firing the event."""
        self.event.set()
        # Fire off one more request so the handle_request() will exit.  XXX
        # Should we set a .timeout on the server instead?
        fp = urlopen('http://localhost:8001/3.0/sys')
        fp.close()
        self.thread.join()

    def loop(self):
        while not self.event.is_set():
            self.server.handle_request()
