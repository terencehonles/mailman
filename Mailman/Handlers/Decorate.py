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

"""Decorate a message by sticking the header and footer around it.
"""

from Mailman import mm_cfg
from Mailman import Utils
import string



def process(mlist, msg):
    d = Utils.SafeDict(mlist.__dict__)
    d['cgiext'] = mm_cfg.CGIEXT
    # interpolate into the header
    header = string.replace(mlist.msg_header % d, '\r\n', '\n')
    footer = string.replace(mlist.msg_footer % d, '\r\n', '\n')
    msg.body = header + msg.body + footer
