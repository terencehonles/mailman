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

"""Netscape Messaging Server bounce formats.

I've seen at least one NMS server version 3.6 (envy.gmp.usyd.edu.au) bounce
messages of this format.  Bounces come in DSN mime format, but don't include
any -Recipient: headers.  Gotta just parse the text :(
"""

import re
import multifile
import mimetools

from Mailman.pythonlib.StringIO import StringIO

pcre = re.compile(r'The following recipients did not receive your message:',
                  re.IGNORECASE)
acre = re.compile(r'<(?P<addr>[^>]*)>')



def process(msg):
    if msg.gettype() <> 'multipart/report' or \
       msg.getparam('report-type') <> 'delivery-status':
        # then
        return None
    boundary = msg.getparam('boundary')
    msg.fp.seek(0)
    mfile = multifile.MultiFile(msg.fp)
    mfile.push(boundary)
    plainmsg = None
    # find the text/plain subpart which must occur before a
    # message/delivery-status part
    while 1:
        try:
            more = mfile.next()
        except multifile.Error, e:
            # the message *looked* like a DSN, but it really wasn't :(
            return None
        if not more:
            # we didn't find it
            return None
        s = StringIO(mfile.read())
        msg = mimetools.Message(s)
        if msg.gettype() == 'message/delivery-status':
            break
        elif msg.gettype() <> 'text/plain':
            # we're looking at something else entirely
            return None
        plainmsg = msg
    # Did we find a text/plain part?
    if not plainmsg:
        return None
    # Total guesswork, based on captured examples...
    addrs = []
    while 1:
        line = plainmsg.fp.readline()
        if not line:
            break
        mo = pcre.search(line)
        if mo:
            # There seems to be an intervening blank line
            line = plainmsg.fp.readline()
            if not line:
                break
            line = plainmsg.fp.readline()
            if not line:
                break
            mo = acre.search(line)
            if mo:
                addrs.append(mo.group('addr'))
    return addrs or None
