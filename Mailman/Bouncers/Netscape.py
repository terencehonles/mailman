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

NMS 4.1 (dfw-smtpin1.email.verio.net) seems even worse, but we'll try to
decipher the format here too.

"""

import string
import re
import multifile
import mimetools

from Mailman.pythonlib.StringIO import StringIO

pcre = re.compile(
    r'This Message was undeliverable due to the following reason:',
    re.IGNORECASE)

acre = re.compile(
    r'(?P<reply>please reply to)?.*<(?P<addr>[^>]*)>',
    re.IGNORECASE)



def process(msg):
    # Sigh.  Some show NMS 3.6's show
    #     multipart/report; report-type=delivery-status
    # and some show
    #     multipart/mixed;
    # TBD: should we tighten this check?
    if msg.getmaintype() <> 'multipart':
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
        except multifile.Error:
            # Not properly formatted MIME
            return None
        if not more:
            # we didn't find it
            return None
        try:
            s = StringIO(mfile.read())
        except multifile.Error:
            # Not properly formatted MIME
            return None
        msg = mimetools.Message(s)
        if msg.getmaintype() == 'message':
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
            # We found a bounce section, but I have no idea what the official
            # format inside here is.  :(  We'll just search for <addr>
            # strings.
            while 1:
                line = plainmsg.fp.readline()
                if not line:
                    break
                mo = acre.search(line)
                if mo and not mo.group('reply'):
                    addrs.append(mo.group('addr'))
    return addrs or None
