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

"""MTA connections."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Connection',
    ]


import logging
import smtplib

from lazr.config import as_boolean
from mailman.config import config


log = logging.getLogger('mailman.smtp')



class Connection:
    """Manage a connection to the SMTP server."""
    def __init__(self, host, port, sessions_per_connection,
                 smtp_user=None, smtp_pass=None):
        """Create a connection manager.

        :param host: The host name of the SMTP server to connect to.
        :type host: string
        :param port: The port number of the SMTP server to connect to.
        :type port: integer
        :param sessions_per_connection: The number of SMTP sessions per
            connection to the SMTP server.  After this number of sessions
            has been reached, the connection is closed and a new one is
            opened.  Set to zero for an unlimited number of sessions per
            connection (i.e. your MTA has no limit).
        :type sessions_per_connection: integer
        :param smtp_user: Optional SMTP authentication user name.  If given,
            `smtp_pass` must also be given.
        :type smtp_user: str
        :param smtp_pass: Optional SMTP authentication password.  If given,
            `smtp_user` must also be given.
        """
        self._host = host
        self._port = port
        self._sessions_per_connection = sessions_per_connection
        self._username = smtp_user
        self._password = smtp_pass
        self._session_count = None
        self._connection = None

    def _connect(self):
        """Open a new connection."""
        self._connection = smtplib.SMTP()
        log.debug('Connecting to %s:%s', self._host, self._port)
        self._connection.connect(self._host, self._port)
        if self._username is not None and self._password is not None:
            log.debug('Logging in')
            self._connection.login(self._username, self._password)
        self._session_count = self._sessions_per_connection

    def sendmail(self, envsender, recipients, msgtext):
        """Mimic `smtplib.SMTP.sendmail`."""
        if as_boolean(config.devmode.enabled):
            # Force the recipients to the specified address, but still deliver
            # to the same number of recipients.
            recipients = [config.devmode.recipient] * len(recipients)
        if self._connection is None:
            self._connect()
        try:
            log.debug('envsender: %s, recipients: %s, size(msgtext): %s',
                      envsender, recipients, len(msgtext))
            results = self._connection.sendmail(envsender, recipients, msgtext)
        except smtplib.SMTPException:
            # For safety, close this connection.  The next send attempt will
            # automatically re-open it.  Pass the exception on up.
            self.quit()
            raise
        # This session has been successfully completed.
        self._session_count -= 1
        # By testing exactly for equality to 0, we automatically handle the
        # case for SMTP_MAX_SESSIONS_PER_CONNECTION <= 0 meaning never close
        # the connection.  We won't worry about wraparound <wink>.
        if self._session_count == 0:
            self.quit()
        return results

    def quit(self):
        """Mimic `smtplib.SMTP.quit`."""
        if self._connection is None:
            return
        try:
            self._connection.quit()
        except smtplib.SMTPException:
            pass
        self._connection = None
