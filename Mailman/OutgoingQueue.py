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

"""Queue up posts if the SMTP connection fails."""
#
# messages are queued before a delivery attempt takes place
# this ensures that should the system fail for some reason,
# the run_queue process will make delivery attempts later.
#
# so q files have 2 possible states - those that are queued because
# they are currently being delivered by the initial delivery attempt
# and those that are queued because the first delivery attempt has
# failed.  the former state is indicated by the fact that the filename
# is setuid.  all queue entries in the latter state are not setuid and
# have data in them.  Since there's no way in python to create a file
# that is setuid at creation time, all files that are empty are
# considered to be in the first state (after the open call but before
# the chmod call).

#
# protection from multiple processQueue procedures occuring
# simultaneously is enforced by setting a lock file forcing
# only one such process to happen at a time.
#

import os, stat, tempfile, marshal, mm_cfg

TEMPLATE = "mm_q."
#
# multiple prcesses with different uids can write and/or
# defer q entries.  with the queue directory setgid to mailman
# and writable by group mailman, having the QF_MODE set to 0660
# should enable any process with gid mailman to read, write, rename,
# or unlink the file
#
QF_MODE = 0660

#
# how long can a q entry possibly be in the
# active state?
#
MAX_ACTIVE = 7200 # 2 hours



#
# 1) get global lock so only of these
#    procedures can run at a time
# 2) find all the files that are deferred queue
#    entries and all the files that have been in
#    an active state for too long and attempt a delivery
#
def processQueue():
    import flock, time, smtplib, Utils
    lock_file = flock.FileLock(os.path.join(mm_cfg.LOCK_DIR, "mmqueue_run.lock"))
    lock_file.lock()
    files = os.listdir(mm_cfg.DATA_DIR)
    for file in files:
        #
        # does it look like a q entry?
        #
        if TEMPLATE != file[:len(TEMPLATE)]:
            continue
        full_fname = os.path.join(mm_cfg.DATA_DIR, file)
        st = os.stat(full_fname)
        #
        # if the file is not a deferred q message, we check to
        # see if the creation time was too long ago and process
        # it anyway.  If the creation time was recent, leave it
        # alone as it's probably being delivered by another process anyway
        #
        if not isDeferred(full_fname) and st[stat.ST_CTIME] > (time.time() - MAX_ACTIVE): 
            continue
        f = open(full_fname,"r")
        recip,sender,text = marshal.load(f)
        f.close()
        Utils.TrySMTPDelivery(recip,sender,text,full_fname)
    lock_file.unlock()



#
# this function is used by any process that
# attempts to deliver a message for the first time
# so the entry is set with the SUID bit.
#
def enqueueMessage(the_sender, recip, text):
    tempfile.tempdir = mm_cfg.DATA_DIR
    tempfile.template = TEMPLATE
    fname = tempfile.mktemp() 
    f = open(fname, "a+")
    os.chmod(fname, QF_MODE | stat.S_ISUID) # make sure this is set right off the bat
    marshal.dump((recip,the_sender,text),f)
    f.close()
    os.chmod(fname, QF_MODE | stat.S_ISUID) # just in case .close() changes the perms
    return fname



#
# is this queue entry a deferred one?
#
def isDeferred(q_entry):
    st = os.stat(q_entry)
    size = st[stat.ST_SIZE]
    mode = st[stat.ST_MODE]
    if mode & stat.S_ISUID: 
        return 0
    elif not size: # the file was just opened, but not yet chmod'd
        return 0
    else:
        return 1
    

#
# given the full path to a q_entry, set the
# status to deferred if it is not
# already in that state.  this function must work
# on entries already in a deferred state.
#
def deferMessage(q_entry):
    if not isDeferred(q_entry):
        os.chmod(q_entry, QF_MODE)


#
# given the full path to a q_entry
# remove it from the queue 
#
def dequeueMessage(q_entry):
    os.unlink(q_entry)







