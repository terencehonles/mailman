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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Yahoo has it's own weird format of bounces."""

import string
import re

tcre = re.compile(r'message\s+from\s+yahoo.com', re.IGNORECASE)
acre = re.compile(r'<(?P<addr>[^>]*)>:')
ecre = re.compile(r'--- Original message follows')



def process(mlist, msg):
    # yahoo bounces seem to have a known subject value and something called an
    # x-uidl header, the value of which seems unimportant
    if msg.get('subject') == 'failed delivery' and msg.get('x-uidl'):
        msg.rewindbody()
        # simple state machine
        #     0 == nothing seen
        #     1 == tag line seen
        state = 0
        while 1:
            line = msg.fp.readline()
            if not line:
                return None
            line = string.strip(line)
            if state == 0 and tcre.match(line):
                state = 1
            elif state == 1:
                mo = acre.match(line)
                if mo:
                    return [mo.group('addr')]
                mo = ecre.match(line)
                if mo:
                    # ain't there
                    return None
