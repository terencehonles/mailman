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

"""Parse messages that contain X-Failed-Recipients headers.
What MTA generates these?
"""

import string



def process(mlist, msg):
    failures = msg.getallmatchingheaders('x-failed-recipients')
    if not failures:
        return None
    addrs = []
    for failed in failures:
        i = string.find(failed, ':')
        if i < 0:
            continue
        addrs.append(string.strip(failed[i+1:]))
    return addrs or None
