# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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

import string
import re
import errno
import mailbox



class Mailbox(mailbox.UnixMailbox):
    # a better regexp than the Python 1.5.2 default
    _fromlinepattern = r'From \s*\S+\s+\w\w\w\s+\w\w\w\s+\d\d?\s+' \
                       r'\d\d?:\d\d(:\d\d)?(\s+\S+)?\s+\d\d\d\d\s*$'
    _regexp = re.compile(_fromlinepattern)

    def _isrealfromline(self, line):
        return self._regexp.match(line)

    # msg should be an rfc822 message or a subclass.
    def AppendMessage(self, msg):
	# Check the last character of the file and write a newline if it isn't
	# a newline (but not at the beginning of an empty file.
        try:
            self.fp.seek(-1, 2)
        except IOError, e:
            # Assume the file is empty.  We can't portably test the error code
            # returned, since it differs per platform.
            pass
        else:
            if self.fp.read(1) <> '\n':
                self.fp.write('\n')
        # seek to the last char of the mailbox
        self.fp.seek(1, 2)
	self.fp.write(msg.unixfrom)
	for line in msg.headers:
	    self.fp.write(line)
	if not msg.body or msg.body[0] <> '\n':
	    self.fp.write('\n')
        # Quote unprotected From_ lines appearing in the body
        for line in string.split(msg.body, '\n'):
            if line[:5] == 'From ' and self._isrealfromline(line):
                self.fp.write('>')
            self.fp.write(line + '\n')
