# Copyright (C) 2001,2002 by the Free Software Foundation, Inc.
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
    wrapper = os.path.join(mm_cfg.WRAPPER_DIR, 'mailman')
    # Most of the list alias extensions are quite regular.  I.e. if the
    # message is delivered to listname-foobar, it will be filtered to a
    # program called foobar.  There are two exceptions:
    #
    # 1) Messages to listname (no extension) go to the post script.
    # 2) Messages to listname-admin go to the bounces script.  This is for
    #    backwards compatibility and may eventually go away (we really have no
    #    need for the -admin address anymore).
    #
    # Seed this with the special cases.
    aliases = [(listname,          '"|%s post %s"' % (wrapper, listname)),
               ]
    for ext in ('admin', 'bounces', 'confirm', 'join', 'leave', 'owner',
                'request', 'subscribe', 'unsubscribe'):
        aliases.append(('%s-%s' % (listname, ext),
                        '"|%s %s %s"' % (wrapper, ext, listname)))
    return aliases
