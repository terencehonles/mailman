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

"""This appear to be Smail's bounce format."""

import string
import re

scre = re.compile(r'failed addresses follow:', re.IGNORECASE)
ecre = re.compile(r'message text follows:', re.IGNORECASE)
acre = re.compile(r'<(?P<addr>[^>]*)>')



def process(msg):
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
        if state == 0:
            mo = scre.search(line)
            if mo:
                state = 1
        elif state == 1:
            mo = ecre.search(line)
            if mo:
                break
            mo = acre.search(line)
            if mo:
                addrs.append(mo.group('addr'))
    return addrs or None
