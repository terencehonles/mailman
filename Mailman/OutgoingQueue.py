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

import os
import stat
import marshal
import errno
import mm_cfg
import Utils

# We need the version of tempfile.py from Python 1.5.2 because it has
# provisions for uniquifying filenames in concurrent children after a fork.
# If not using Python 1.5.2's version, let's get our copy of the new file.
import tempfile
if not hasattr(tempfile, '_pid'):
    from Mailman.pythonlib import tempfile
assert hasattr(tempfile, '_pid')

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
    import flock
    import time
    import Utils

    lock_file = flock.FileLock(
        os.path.join(mm_cfg.LOCK_DIR, "mmqueue_run.lock"))
    lock_file.lock()
    files = os.listdir(mm_cfg.DATA_DIR)
    for file in files:
        #
        # does it look like a queue entry?
        #
        if TEMPLATE != file[:len(TEMPLATE)]:
            continue
        full_fname = os.path.join(mm_cfg.DATA_DIR, file)
        #
        # we need to stat the file if it still exists (atomically, we can't
        # just use use os.path.exists then stat it.  if it doesn't exist, it's
        # been dequeued since we saw it in the directory listing
        #
        try:
            st = os.stat(full_fname)
        except os.error, (code, msg):
            if code == errno.ENOENT:
                # file does not exist, it's already been dequeued
                continue
            else:
                Utils.reraise()
        #
        # if the file is not a deferred queue message, we check to see if the
        # creation time was too long ago and process it anyway.  If the
        # creation time was recent, leave it alone as it's probably being
        # delivered by another process anyway
        #
        if (not isDeferred(full_fname, st) and
            st[stat.ST_CTIME] > (time.time() - MAX_ACTIVE)):
            # then
            continue
        f = open(full_fname,"r")
        recip,sender,text = marshal.load(f)
        f.close()
        Utils.TrySMTPDelivery(recip,sender,text,full_fname)
    lock_file.unlock()


#
# this function is used by any process that
# attempts to deliver a message for the first time
# so the entry is set with the SUID bit.  With all these
# concurrent processes calling this function, we can't quite
# trust mktemp() to generate a unique filename, and with the
# possibility of a q entry lasting longer than the pid generation
# cycle on the system we can't quite trust os.getpid() to return
# a unique filename either.  but if we use getpid() in the
# template, then mktemp should always return a unique filename.
#
def enqueueMessage(the_sender, recip, text):
    tempfile.tempdir = mm_cfg.DATA_DIR
    tempfile.template = "%s%d." % (TEMPLATE, os.getpid())
    fname = tempfile.mktemp() 
    #
    # open the file so that it is setuid upon creation
    #
    f = Utils.open_ex(fname, "a+", -1, QF_MODE | stat.S_ISUID)
    marshal.dump((recip,the_sender,text),f)
    f.close()
    return fname


#
# is this queue entry a deferred one?
#
def isDeferred(q_entry, st=None):
    if st is None:
        st = os.stat(q_entry)
    if st[stat.ST_MODE] & stat.S_ISUID: 
        return 0
    else:
        return 1


#
# given the full path to a q_entry, set the
# status to deferred if it is not
# already in that state.  this function must work
# on entries already in a deferred state.
# this function may only be called by the process
# that called enqueueMessage(), since it uses chmod
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
