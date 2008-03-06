# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""A test SMTP listener."""

import smtpd
import asyncore

from email import message_from_string

COMMASPACE = ', '



class Channel(smtpd.SMTPChannel):
    """A channel that can reset the mailbox."""

    def __init__(self, server, conn, addr):
        smtpd.SMTPChannel.__init__(self, server, conn, addr)
        # Stash this here since the subclass uses private attributes. :(
        self._server = server

    def smtp_EXIT(self, arg):
        """Respond to a new command EXIT by exiting the server."""
        self.push('250 Ok')
        self._server.stop()

    def send(self, data):
        """Silence the bloody asynchat/asyncore broken pipe errors!"""
        try:
            return smtpd.SMTPChannel.send(self, data)
        except socket.error:
            # Nothing here can affect the outcome, and these messages are just
            # plain annoying!  So ignore them.
            pass



class Server(smtpd.SMTPServer):
    """An SMTP server that stores messages to a mailbox."""

    def __init__(self, localaddr, queue):
        smtpd.SMTPServer.__init__(self, localaddr, None)
        self._queue = queue

    def handle_accept(self):
        """Handle connections by creating our own Channel object."""
        conn, addr = self.accept()
        Channel(self, conn, addr)

    def process_message(self, peer, mailfrom, rcpttos, data):
        """Process a message by adding it to the mailbox."""
        message = message_from_string(data)
        message['X-Peer'] = peer
        message['X-MailFrom'] = mailfrom
        message['X-RcptTo'] = COMMASPACE.join(rcpttos)
        self._queue.put(message)

    def start(self):
        """Start the asyncore loop."""
        asyncore.loop()

    def stop(self):
        """Stop the asyncore loop."""
        asyncore.socket_map.clear()
        asyncore.close_all()
        self.close()
