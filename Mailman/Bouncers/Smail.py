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

"""This appear to be Smail's bounce format."""

import string
import re

introtag = '|------------------------- ' \
           'Failed addresses follow: ---------------------|'
endtag   = '|------------------------- ' \
           'Message text follows: ------------------------|'

acre = re.compile(r'\s*address:\s*<(?P<addr>[^>]*)>')


def process(mlist, msg):
    msg.rewindbody()
    # simple state machine
    #    0 = nothing seen yet
    #    1 = intro line seen
    state = 0
    addrs = []
    while 1:
        line = msg.fp.readline()
        if not line:
            break
        line = string.strip(line)
        if state == 0 and line == introtag:
            state = 1
        elif state == 2 and line == endtag:
            break
        mo = acre.match(line)
        if mo:
            addrs.append(mo.group('addr'))
        # don't know what we're looking at
    return addrs or None
