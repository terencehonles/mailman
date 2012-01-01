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

"""Fake MTA for testing purposes."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'FakeMTA',
    ]


import logging

from Queue import Empty, Queue

from lazr.smtptest.controller import QueueController
from lazr.smtptest.server import Channel, QueueServer
from zope.interface import implements

from mailman.interfaces.mta import IMailTransportAgentLifecycle


log = logging.getLogger('lazr.smtptest')



class FakeMTA:
    """Fake MTA for testing purposes."""

    implements(IMailTransportAgentLifecycle)

    def create(self, mlist):
        pass

    def delete(self, mlist):
        pass

    def regenerate(self, output=None):
        pass



class StatisticsChannel(Channel):
    """A channel that can answers to the fake STAT command."""

    def smtp_EHLO(self, arg):
        if not arg:
            self.push(b'501 Syntax: HELO hostname')
            return
        if self._SMTPChannel__greeting:
            self.push(b'503 Duplicate HELO/EHLO')
        else:
            self._SMTPChannel__greeting = arg
            self.push(b'250-%s' % self._SMTPChannel__fqdn)
            self.push(b'250 AUTH PLAIN')

    def smtp_STAT(self, arg):
        """Cause the server to send statistics to its controller."""
        self._server.send_statistics()
        self.push(b'250 Ok')

    def smtp_AUTH(self, arg):
        """Record that the AUTH occurred."""
        if arg == 'PLAIN AHRlc3R1c2VyAHRlc3RwYXNz':
            # testuser:testpass
            self.push(b'235 Ok')
            self._server.send_auth(arg)
        else:
            self.push(b'571 Bad authentication')

    def smtp_RCPT(self, arg):
        """For testing, sometimes cause a non-25x response."""
        code = self._server.next_error('rcpt')
        if code is None:
            # Everything's cool.
            Channel.smtp_RCPT(self, arg)
        else:
            # The test suite wants this to fail.  The message corresponds to
            # the exception we expect smtplib.SMTP to raise.
            self.push(b'%d Error: SMTPRecipientsRefused' % code)

    def smtp_MAIL(self, arg):
        """For testing, sometimes cause a non-25x response."""
        code = self._server.next_error('mail')
        if code is None:
            # Everything's cool.
            Channel.smtp_MAIL(self, arg)
        else:
            # The test suite wants this to fail.  The message corresponds to
            # the exception we expect smtplib.SMTP to raise.
            self.push(b'%d Error: SMTPResponseException' % code)



class ConnectionCountingServer(QueueServer):
    """Count the number of SMTP connections opened."""

    def __init__(self, host, port, queue, oob_queue, err_queue):
        """See `lazr.smtptest.server.QueueServer`.

        :param oob_queue: A queue for communicating information back to the
            controller, e.g. statistics.
        :type oob_queue: `Queue.Queue`
        :param err_queue: A queue for allowing the controller to request SMTP
            errors from the server.
        :type err_queue: `Queue.Queue`
        """
        QueueServer.__init__(self, host, port, queue)
        self._connection_count = 0
        self.last_auth = None
        # The out-of-band queue is where the server sends statistics to the
        # controller upon request.
        self._oob_queue = oob_queue
        self._err_queue = err_queue
        self._last_error = None

    def next_error(self, command):
        """Return the next error for the SMTP command, if there is one.

        :param command: The SMTP command for which an error might be
            expected.  If the next error matches the given command, the
            expected error code is returned.
        :type command: string, lower-cased
        :return: An SMTP error code
        :rtype: integer
        """
        # If the last error we pulled from the queue didn't match, then we're
        # caching it, and it might match this expected error.  If there is no
        # last error in the cache, get one from the queue now.
        if self._last_error is None:
            try:
                self._last_error = self._err_queue.get_nowait()
            except Empty:
                # No error is expected
                return None
        if self._last_error[0] == command:
            code = self._last_error[1]
            self._last_error = None
            return code
        return None

    def handle_accept(self):
        """See `lazr.smtp.server.Server`."""
        connection, address = self.accept()
        self._connection_count += 1
        log.info('[ConnectionCountingServer] accepted: %s', address)
        StatisticsChannel(self, connection, address)

    def reset(self):
        """See `lazr.smtp.server.Server`."""
        QueueServer.reset(self)
        self._connection_count = 0

    def send_statistics(self):
        """Send the current connection statistics to the controller."""
        # Do not count the connection caused by the STAT connect.
        self._connection_count -= 1
        self._oob_queue.put(self._connection_count)

    def send_auth(self, arg):
        """Echo back the authentication data."""
        self._oob_queue.put(arg)



class ConnectionCountingController(QueueController):
    """Count the number of SMTP connections opened."""

    def __init__(self, host, port):
        """See `lazr.smtptest.controller.QueueController`."""
        self.oob_queue = Queue()
        self.err_queue = Queue()
        QueueController.__init__(self, host, port)

    def _make_server(self, host, port):
        """See `lazr.smtptest.controller.QueueController`."""
        self.server = ConnectionCountingServer(
            host, port, self.queue, self.oob_queue, self.err_queue)

    def start(self):
        """See `lazr.smtptest.controller.QueueController`."""
        QueueController.start(self)
        # Reset the connection statistics, since the base class's start()
        # method causes a connection to occur.
        self.reset()

    def get_connection_count(self):
        """Retrieve the number of connections.

        :return: The number of connections to the server that have been made.
        :rtype: integer
        """
        smtpd = self._connect()
        smtpd.docmd(b'STAT')
        # An Empty exception will occur if the data isn't available in 10
        # seconds.  Let that propagate.
        return self.oob_queue.get(block=True, timeout=10)

    def get_authentication_credentials(self):
        """Retrieve the last authentication credentials."""
        return self.oob_queue.get(block=True, timeout=10)

    @property
    def messages(self):
        """Return all the messages received by the SMTP server."""
        for message in self:
            yield message

    def clear(self):
        """Clear all the messages from the queue."""
        list(self)

    def reset(self):
        smtpd = self._connect()
        smtpd.docmd(b'RSET')
