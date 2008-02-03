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

import sys
import smtpd
import signal
import mailbox
import asyncore
import optparse

from email import message_from_string

COMMASPACE = ', '
DEFAULT_PORT = 9025



class Channel(smtpd.SMTPChannel):
    """A channel that can reset the mailbox."""

    def __init__(self, server, conn, addr):
        smtpd.SMTPChannel.__init__(self, server, conn, addr)
        # Stash this here since the subclass uses private attributes. :(
        self._server = server

    def smtp_RSET(self, arg):
        """Respond to RSET and clear the mailbox."""
        self._server.clear_mailbox()
        smtpd.SMTPChannel.smtp_RSET(self, arg)

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

    def __init__(self, localaddr, mailbox_path):
        smtpd.SMTPServer.__init__(self, localaddr, None)
        self._mailbox = mailbox.Maildir(mailbox_path)

    def handle_accept(self):
        """Handle connections by creating our own Channel object."""
        conn, addr = self.accept()
        Channel(self, conn, addr)

    def process_message(self, peer, mailfrom, rcpttos, data):
        """Process a message by adding it to the mailbox."""
        msg = message_from_string(data)
        msg['X-Peer'] = peer
        msg['X-MailFrom'] = mailfrom
        msg['X-RcptTo'] = COMMASPACE.join(rcpttos)
        self._mailbox.add(msg)
        self._mailbox.clean()



def handle_signal(*ignore):
    """Handle signal sent by parent to kill the process."""
    asyncore.socket_map.clear()



def main():
    parser = optparse.OptionParser(usage="""\
%prog [options] mboxfile

This starts a process listening on a specified host and port (by default
localhost:9025) for SMTP conversations.  All messages this process receives
are stored in a specified mbox file for the parent process to investigate.

This SMTP server responds to RSET commands by clearing the mbox file.
""")
    parser.add_option('-a', '--address',
                      type='string', default=None,
                      help='host:port to listen on')
    opts, args = parser.parse_args()
    if len(args) == 0:
        parser.error('Missing mbox file')
    elif len(args) > 1:
        parser.error('Unexpected arguments')

    mboxfile = args[0]
    if opts.address is None:
        host = 'localhost'
        port = DEFAULT_PORT
    elif ':' not in opts.address:
        host = opts.address
        port = DEFAULT_PORT
    else:
        host, port = opts.address.split(':', 1)
        port = int(port)

    # Catch the parent's exit signal, and also C-c.
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    server = Server((host, port), mboxfile)
    asyncore.loop()
    asyncore.close_all()
    server.close()
    return 0



if __name__ == '__main__':
    sys.exit(main())
