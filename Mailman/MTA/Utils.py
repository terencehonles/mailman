# Copyright (C) 2001 by the Free Software Foundation, Inc.
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

"""Utilities for list creation/deletion hooks."""

import os
import pwd

from Mailman import mm_cfg



def getusername():
    username = os.environ.get('USER') or os.environ.get('LOGNAME')
    if not username:
        import pwd
        username = pwd.getpwuid(os.getuid())[0]
    if not username:
        username = '<unknown>'
    return username



def makealiases(listname):
    wrapper = os.path.join(mm_cfg.WRAPPER_DIR, 'wrapper')
    return (
        (listname,              '"|%s post %s"'      % (wrapper, listname)),
        (listname + '-admin',   '"|%s mailowner %s"' % (wrapper, listname)),
        (listname + '-request', '"|%s mailcmd %s"'   % (wrapper, listname)),
        (listname + '-join',    '"|%s join %s"'      % (wrapper, listname)),
        (listname + '-leave',   '"|%s leave %s"'      % (wrapper, listname)),
        (listname + '-owner',   '%s-admin' % listname),
        )
