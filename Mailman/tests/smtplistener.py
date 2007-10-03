# Copyright (C) 2007 by the Free Software Foundation, Inc.
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

import sys
import smtpd
import mailbox
import asyncore
import optparse

from email import message_from_string

COMMASPACE = ', '
DEFAULT_PORT = 9025



class Channel(smtpd.SMTPChannel):
    def smtp_EXIT(self, arg):
        raise asyncore.ExitNow


class Server(smtpd.SMTPServer):
    def __init__(self, localaddr, mboxfile):
        smtpd.SMTPServer.__init__(self, localaddr, None)
        self._mbox = mailbox.mbox(mboxfile)

    def handle_accept(self):
        conn, addr = self.accept()
        Channel(self, conn, addr)

    def process_message(self, peer, mailfrom, rcpttos, data):
        msg = message_from_string(data)
        msg['X-Peer'] = peer
        msg['X-MailFrom'] = mailfrom
        msg['X-RcptTo'] = COMMASPACE.join(rcpttos)
        self._mbox.add(msg)

    def close(self):
        self._mbox.flush()
        self._mbox.close()



def main():
    parser = optparse.OptionParser(usage='%prog mboxfile')
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

    server = Server((host, port), mboxfile)
    try:
        asyncore.loop()
    except asyncore.ExitNow:
        asyncore.close_all()
        server.close()
    return 0



if __name__ == '__main__':
    sys.exit(main())
