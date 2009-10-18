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

"""Fake MTA for testing purposes."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'FakeMTA',
    ]


import logging

from Queue import Queue

from lazr.smtptest.controller import QueueController
from lazr.smtptest.server import Channel, QueueServer
from zope.interface import implements

from mailman.interfaces.mta import IMailTransportAgent


log = logging.getLogger('lazr.smtptest')



class FakeMTA:
    """Fake MTA for testing purposes."""

    implements(IMailTransportAgent)

    def create(self, mlist):
        pass

    def delete(self, mlist):
        pass

    def regenerate(self):
        pass



class SessionCountingChannel(Channel):
    """Count the number of SMTP sessions opened and closed."""

    def smtp_STAT(self, arg):
        """Cause the server to send statistics to its controller."""
        self._server.send_statistics()
        self.push('250 Ok')



class SessionCountingServer(QueueServer):
    """Count the number of SMTP sessions opened and closed."""

    def __init__(self, host, port, queue, oob_queue):
        """See `lazr.smtptest.server.QueueServer`."""
        QueueServer.__init__(self, host, port, queue)
        self.session_count = 0
        # The out-of-band queue is where the server sends statistics to the
        # controller upon request.
        self._oob_queue = oob_queue

    def handle_accept(self):
        """See `lazr.smtp.server.Server`."""
        connection, address = self.accept()
        self.session_count += 1
        log.info('[SessionCountingServer] accepted: %s', address)
        SessionCountingChannel(self, connection, address)

    def reset(self):
        """See `lazr.smtp.server.Server`."""
        QueueServer.reset(self)
        self.session_count = 0

    def send_statistics(self):
        """Send the current connection statistics to the controller."""
        # Do not count the connection caused by the STAT connect.
        self.session_count -= 1
        self._oob_queue.put(self.session_count)



class SessionCountingController(QueueController):
    """Count the number of SMTP sessions opened and closed."""

    def __init__(self, host, port):
        """See `lazr.smtptest.controller.QueueController`."""
        self.oob_queue = Queue()
        QueueController.__init__(self, host, port)

    def _make_server(self, host, port):
        """See `lazr.smtptest.controller.QueueController`."""
        self.server = SessionCountingServer(
            host, port, self.queue, self.oob_queue)

    def start(self):
        """See `lazr.smtptest.controller.QueueController`."""
        QueueController.start(self)
        # Reset the connection statistics, since the base class's start()
        # method causes a connection to occur.
        self.reset()

    def get_session_count(self):
        """Retrieve the number of sessions.

        :return: The number of sessions that have been opened.
        :rtype: integer
        """
        smtpd = self._connect()
        smtpd.docmd('STAT')
        # An Empty exception will occur if the data isn't available in 10
        # seconds.  Let that propagate.
        return self.oob_queue.get(block=True, timeout=10)

    @property
    def messages(self):
        """Return all the messages received by the SMTP server."""
        for message in self:
            yield message

    def clear(self):
        """Clear all the messages from the queue."""
        list(self)
