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

"""Microsoft's `SMTPSVC' nears I kin tell."""

import string
import re
import multifile

from Mailman.pythonlib.StringIO import StringIO

scre = re.compile(r'transcript of session follows', re.IGNORECASE)



def process(msg):
    if msg.gettype() <> 'multipart/mixed':
        return None
    boundary = msg.getparam('boundary')
    msg.fp.seek(0)
    addrs = []
    try:
        mfile = multifile.MultiFile(msg.fp)
        mfile.push(boundary)
        # find the first subpart, which has no mime type
        try:
            more = mfile.next()
        except multifile.Error:
            # the message *looked* like a DSN, but it really wasn't :(
            return None
        if not more:
            # we didn't find it
            return None
        # simple state machine
        #    0 == nothng seen yet
        #    1 == tag line seen
        state = 0
        while 1:
            line = mfile.readline()
            if not line:
                break
            line = string.strip(line)
            if state == 0:
                if scre.search(line):
                    state = 1
            if state == 1:
                if '@' in line:
                    addrs.append(line)
    except multifile.Error:
        pass
    return addrs
