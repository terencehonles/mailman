# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


"Extend mailbox.UnixMailbox."

from email.Generator import Generator
from email.Parser import Parser

from Mailman.Message import Message
from Mailman.pythonlib import mailbox




# Factory callable for UnixMailboxes.  This ensures that any object we get out
# of the mailbox is an instance of our subclass.  (requires Python 2.1's
# mailbox module)
def _factory(fp):
    p = Parser(Message)
    return p.parse(fp)



class Mailbox(mailbox.PortableUnixMailbox):
    def __init__(self, fp):
        mailbox.PortableUnixMailbox.__init__(self, fp, _factory)

    # msg should be an rfc822 message or a subclass.
    def AppendMessage(self, msg):
	# Check the last character of the file and write a newline if it isn't
	# a newline (but not at the beginning of an empty file).
        try:
            self.fp.seek(-1, 2)
        except IOError, e:
            # Assume the file is empty.  We can't portably test the error code
            # returned, since it differs per platform.
            pass
        else:
            if self.fp.read(1) <> '\n':
                self.fp.write('\n')
        # Seek to the last char of the mailbox
        self.fp.seek(1, 2)
        # Create a Generator instance to write the message to the file
        g = Generator(self.fp)
        g(msg, unixfrom=1)
