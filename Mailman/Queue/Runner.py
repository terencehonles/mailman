#! /usr/bin/env python
#
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

"""Generic queue runner class.
"""

import os
import marshal
import random
import time

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman import MailList
from Mailman import Message
from Mailman import LockFile
from Mailman.Logging.Syslog import syslog



class Runner:
    def __init__(self, qdir, cachelists=1):
        self._qdir = qdir
        self._kids = {}
        self._cachelists = cachelists
        self._lock = LockFile.LockFile(os.path.join(qdir, 'qrunner.lock'),
                                       lifetime = mm_cfg.QRUNNER_LOCK_LIFETIME)

    def _dequeue(self, filebase):
        os.unlink(filebase + '.db')
        os.unlink(filebase + '.msg')

    _listcache = {}

    def _open_list(self, listname, lockp=1):
        if self._cachelists:
            mlist = self._listcache.get(listname)
        else:
            mlist = None
        if not mlist:
            try:
                mlist = MailList.MailList(listname, lock=0)
                if self._cachelists:
                    self._listcache[listname] = mlist
            except Errors.MMListError, e:
                syslog('qrunner', 'error opening list: %s\n%s' % (listname, e))
                return None
        return mlist

    def _start(self):
        self._msgcount = 0
        self._t0 = time.time()
        try:
            self._lock.lock(timeout=0.5)
        except LockFile.TimeOutError:
            # Some other qrunner process is running, which is fine.
            syslog('qrunner', 'Could not acquire %s lock' %
                   self.__class__)
            return 0
        return 1

    def _cleanup(self):
        Utils.reap(self._kids)
        self._listcache.clear()

    def _onefile(self, filebase):
        msgfp = dbfp = None
        try:
            dbfp = open(filebase + '.db')
            msgdata = marshal.load(dbfp)
            dbfp.close()
            dbfp = None
            msgfp = open(filebase + '.msg')
            # re-establish the file base for re-queuing
            msg = Message.Message(msgfp, filebase=msgdata.get('filebase'))
            msgfp.close()
            msgfp = None
        except (EOFError, ValueError, TypeError, IOError), e:
            # For some reason we had trouble getting all the information out
            # of the queued files.  log this and move on (we figure it's a
            # temporary problem)
            syslog('qrunner',
                   'Exception reading qfiles: %s\n%s' % (filebase, e))
            if msgfp:
                msgfp.close()
            if dbfp:
                dbfp.close()
            return
        keepqueued = self._dispose_message(msg, msgdata)
        # Did the delivery generate child processes?
        kids = msgdata.get('_kids')
        if kids:
            self._kids.update(kids)
            del msgdata['_kids']
        if not keepqueued:
            # We're done with this message
            self._dequeue(filebase)

    def _dispose_message(self, msg, msgdata):
        raise UnimplementedError

    def _doperiodic(self):
        if mm_cfg.QRUNNER_MAX_MESSAGES is not None and \
           self._msgcount > mm_cfg.QRUNNER_MAX_MESSAGES:
            return 0
        if mm_cfg.QRUNNER_PROCESS_LIFETIME is not None and \
           (time.time() - self._t0) > mm_cfg.QRUNNER_PROCESS_LIFETIME:
            return 0
        self._msgcount += 1
        return 1

    def run(self):
        # Give us the absolute path to all the unique filebase file names in
        # the current directory.
        files = []
        for file in os.listdir(self._qdir):
            root, ext = os.path.splitext(file)
            if ext == '.db':
                files.append(os.path.join(self._qdir, root))
        # Randomize this list so we're more likely to touch them all
        # eventually, even if we're hitting resource limits.
        random.shuffle(files)
        # initialize the resource counters
        okaytostart = self._start()
        if not okaytostart:
            return
        for filebase in files:
            keepgoing = self._doperiodic()
            if not keepgoing:
                break
            self._onefile(filebase)
        # clean up after ourselves
        self._cleanup()
