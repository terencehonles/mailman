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

"""Parse RFC 1894 (i.e. DSN) bounce formats."""

import string
import multifile
import mimetools

from Mailman.pythonlib.StringIO import StringIO



def parseaddr(val):
    atype, addr = string.split(val, ';')
    if string.lower(string.strip(atype)) <> 'rfc822':
        return None
    addr = string.strip(addr)
    if not addr:
        return None
    # strip off <>
    if addr[0] == '<' and addr[-1] == '>':
        return addr[1:-1]



def process(mlist, msg):
    if msg.gettype() <> 'multipart/report' or \
       msg.getparam('report-type') <> 'delivery-status':
        # then
        return None
    boundary = msg.getparam('boundary')
    msg.fp.seek(0)
    mfile = multifile.MultiFile(msg.fp)
    mfile.push(boundary)
    # find the subpart with message/delivery-status information
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
        msg2 = mimetools.Message(s)
        if msg2.gettype() == 'message/delivery-status':
            # hmm, could there be more than one DSN per message?
            break
    # now parse out the per-recipient fields, which are separated by blank
    # lines.  the first block is actually the per-notification fields, but
    # those can be safely ignored
    #
    # we try to dig out the Original-Recipient (which is optional) and
    # Final-Recipient (which is mandatory, but may not exactly match an addr
    # on our list).  Also grok out Action so we can do something with that
    # too.
    recips = []
    orig = final = action = None
    while 1:
        line = msg2.fp.readline()
        if not line:
            break
        line = string.strip(line)
        if not line:
            # a new recipient block
            if final:
                recips.append((final, orig, action))
            orig = final = action = None
            continue
        try:
            hdr, val = string.split(line, ':', 1)
        except ValueError:
            continue
        hdr = string.lower(hdr)
        val = string.strip(val)
        if not orig and hdr == 'original-recipient':
            orig = parseaddr(val)
        elif not final and hdr == 'final-recipient':
            final = parseaddr(val)
        elif not action and hdr == 'action':
            action = val
        # ignore everything else
    # now collapse recipients
    finals = {}
    for final, orig, action in recips:
        o, a = finals.get(final, (None, None))
        if not o:
            finals[final] = orig, action
        elif a <> 'failed' and action == 'failed':
            finals[final] = orig, action
    addrs = []
    for final, (orig, action) in finals.items():
        addrs.append(orig or final)
    return addrs
