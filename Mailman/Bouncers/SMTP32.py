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

"""Something which claims
X-Mailer: <SMTP32 vXXXXXX>

What the heck is this thing?
"""

import re
from mimelib import MsgReader

ecre = re.compile('original message follows', re.IGNORECASE)
acre = re.compile(r'user mailbox[^:]*:\s*(?P<addr>.*)', re.IGNORECASE)



def process(msg):
    mi = MsgReader.MsgReader(msg)
    addrs = {}
    while 1:
        line = mi.readline()
        if not line:
            break
        if ecre.search(line):
            break
        mo = acre.search(line)
        if mo:
            addrs[mo.group('addr')] = 1
    return addrs.keys()
