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

"""Recognizes simple heuristically delimited bounces."""

import re

def _c(pattern):
    return re.compile(pattern, re.IGNORECASE)

patterns = [
    # sdm.de
    (_c('here is your list of failed recipients'),
     _c('here is your returned mail'),
     _c(r'<(?P<addr>[^>]*)>')),
    # sz-sb.de, corridor.com
    (_c('the following addresses had'),
     _c('transcript of session follows'),
     _c(r'<(?P<addr>[^>]*)>')),
    # robanal.demon.co.uk
    (_c('this message was created automatically by mail delivery software'),
     _c('original message follows'),
     _c('rcpt to:\s*<(?P<addr>[^>]*)>')),
    # s1.com (InterScan E-Mail VirusWall NT ???)
    (_c('message from interscan e-mail viruswall nt'),
     _c('end of message'),
     _c('rcpt to:\s*<(?P<addr>[^>]*)>')),
    ]




def process(msg):
    msg.rewindbody()
    # simple state machine
    #     0 = nothing seen yet
    #     1 = intro seen
    addrs = {}
    state = 0
    while 1:
        line = msg.fp.readline()
        if not line:
            break
        if state == 0:
            for scre, ecre, acre in patterns:
                if scre.search(line):
                    state = 1
                    break
        elif state == 1:
            mo = acre.search(line)
            if mo:
                addrs[mo.group('addr')] = 1
            elif ecre.search(line):
                break
    return addrs.keys() or None
