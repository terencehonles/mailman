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

"""Creation/deletion hooks for the Postfix MTA.

Note: only hash: type maps are currently supported.
"""

import os
import socket
import time
import dbhash
import errno

from Mailman import mm_cfg



def _addlist(listname, db):
    wrapper = os.path.join(mm_cfg.WRAPPER_DIR, 'wrapper')
    # Every key and value in the dbhash file as created by Postfix must end in
    # a null byte.  That is, except YP_LAST_MODIFIED and YP_MASTER_NAME.
    db[listname + '\0'] = '"|%s post %s"\0' % (wrapper, listname)
    db[listname + '-admin\0'] = '"|%s mailowner %s"\0' % (wrapper, listname)
    db[listname + '-owner\0'] = '%s-admin\0' % listname
    db[listname + '-request\0'] = '"|%s mailcmd %s"\0' % (wrapper, listname)
    # Always update YP_LAST_MODIFIED
    db['YP_LAST_MODIFIED'] = '%010d' % time.time()
    # Add a YP_MASTER_NAME only if there isn't one already
    if not db.has_key('YP_MASTER_NAME'):
        db['YP_MASTER_NAME'] = socket.getfqdn()



def _rmlist(listname, db):
    for extra in ('', '-admin', '-owner', '-request'):
        try:
            del db[listname + extra + '\0']
        except KeyError:
            pass
    # Always update YP_LAST_MODIFIED
    db['YP_LAST_MODIFIED'] = '%010d' % time.time()
    # Add a YP_MASTER_NAME only if there isn't one already
    if not db.has_key('YP_MASTER_NAME'):
        db['YP_MASTER_NAME'] = socket.getfqdn()



def create(mlist):
    listname = mlist.internal_name()
    db = dbhash.open(os.path.join(mm_cfg.DATA_DIR, 'aliases.db'), 'c')
    _addlist(listname, db)
    db.sync()



def remove(mlist):
    listname = mlist.internal_name()
    db = dbhash.open(os.path.join(mm_cfg.DATA_DIR, 'aliases.db'), 'c')
    _rmlist(listname, db)
    db.sync()
