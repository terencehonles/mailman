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

"""
Module for handling pending subscriptions
"""

import os 
import sys
import posixfile
import marshal
import time
import whrandom
import mm_cfg
import flock

DB_PATH = os.path.join(mm_cfg.DATA_DIR,"pending_subscriptions.db")
LOCK_PATH = os.path.join(mm_cfg.LOCK_DIR, "pending_subscriptions.lock")


def get_pending():
    " returns a dict containing pending information"
    try:
        fp = open(DB_PATH,"r" )
    except IOError:
        return {}
    dict = marshal.load(fp)
    return dict


def gencookie(p=None):
    if p is None:
        p = get_pending()
    while 1:
        newcookie = int(whrandom.random() * 1000000)
        if p.has_key(newcookie) or newcookie < 100000:
            continue
        return newcookie

def set_pending(p):
    lock_file = flock.FileLock(LOCK_PATH)
    lock_file.lock()
    fp = open(DB_PATH, "w") 
    marshal.dump(p, fp) 
    fp.close() 
    lock_file.unlock()

def add2pending(email_addr, password, digest, cookie): 
    ts = int(time.time())
    processed = 0
    p = get_pending()
    p[cookie] = (email_addr, password, digest,  ts)
    set_pending(p)


