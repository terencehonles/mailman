# Copyright (C) 1998 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 0211-1307, USA.


"Extend mailbox.UnixMailbox."

__version__ = "$Revision: 539 $"


import mailbox

class Mailbox(mailbox.UnixMailbox):
    # msg should be an rfc822 message or a subclass.
    def AppendMessage(self, msg):
	# seek to the last char of the mailbox
	self.fp.seek(1,2)
	if self.fp.read(1) <> '\n':
	    self.fp.write('\n')
	self.fp.write(msg.unixfrom)
	for line in msg.headers:
	    self.fp.write(line)
	if msg.body[0] <> '\n':
	    self.fp.write('\n') 
	self.fp.write(msg.body)
	
