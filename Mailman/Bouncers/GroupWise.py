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

"""This appears to be the format for Novell GroupWise and NTMail

X-Mailer: Novell GroupWise Internet Agent 5.5.3.1
X-Mailer: NTMail v4.30.0012
"""

import string
import re
import mimetools
import multifile

from Mailman.pythonlib.StringIO import StringIO

acre = re.compile(r'<(?P<addr>[^>]*)>')



def process(msg):
    if msg.gettype() <> 'multipart/mixed':
        return None
    addrs = {}
    boundary = msg.getparam('boundary')
    msg.rewindbody()
    mfile = multifile.MultiFile(msg.fp)
    try:
        mfile.push(boundary)
        while 1:
            if not mfile.next():
                return None
            msg2 = mimetools.Message(StringIO(mfile.read()))
            if msg2.gettype() == 'text/plain':
                # Hmm, could there be more than one part per message?
                break
        msg2.rewindbody()
        while 1:
            line = string.strip(msg2.fp.readline())
            if not line:
                break
            mo = acre.search(line)
            if mo:
                addrs[mo.group('addr')] = 1
            elif '@' in line:
                i = string.find(line, ' ')
                if i < 0:
                    addrs[line] = 1
                else:
                    addrs[line[:i]] = 1
    except multifile.Error:
        pass
    return addrs.keys() or None
