# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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

import random
import time
import traceback

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman import MailList

from Mailman.pythonlib.StringIO import StringIO
from Mailman.Queue.Switchboard import Switchboard
from Mailman.Logging.Syslog import syslog



class Runner:
    def __init__(self, qdir, slice=None, numslices=1, cachelists=1):
        self._qdir = qdir
        self._kids = {}
        self._cachelists = cachelists
        # Create our own switchboard.  Don't use the switchboard cache because
        # we want to provide slice and numslice arguments.
        self._switchboard = Switchboard(qdir, slice, numslices)
        # Create the shunt switchboard
        self._shunt = Switchboard(mm_cfg.SHUNTQUEUE_DIR)
        self._stop = 0

    def stop(self):
        self._stop = 1

    def run(self):
        # Start the main loop for this queue runner.
        try:
            try:
                while 1:
                    # Once through the loop that processes all the files in
                    # the queue directory.
                    filecnt = self.__oneloop()
                    # Do the periodic work for the subclass.
                    self._doperiodic()
                    # If the stop flag is set, we're done.
                    if self._stop:
                        break
                    # If there were no files to process, then we'll simply
                    # sleep for a little while and expect some to show up.
                    if filecnt == 0:
                        self._snooze()
            except KeyboardInterrupt:
                pass
        finally:
            # We've broken out of our main loop, so we want to reap all the
            # subprocesses we've created and do any other necessary cleanups.
            self._cleanup()

    def __oneloop(self):
        # First, list all the files in our queue directory, and randomize them
        # for better coverage even at resource limits.
        files = self._switchboard.files()
        random.shuffle(files)
        for filebase in files:
            # Ask the switchboard for the message and metadata objects
            # associated with this filebase.
            msg, msgdata = self._switchboard.dequeue(filebase)
            # Now that we've dequeued the message, we want to be incredibly
            # anal about making sure that no uncaught exception could cause us
            # to lose the message.  All runners that implement _dispose() must
            # guarantee that exceptions are caught and dealt with properly.
            # Still, there may be a bug in the infrastructure, and we do not
            # want those to cause messages to be lost.  Any uncaught
            # exceptions will cause the message to be stored in the shunt
            # queue for human intervention.
            try:
                self.__onefile(msg, msgdata)
            except Exception, e:
                self._log(e)
                self._shunt.enqueue(msg, msgdata)
            # Other work we want to do each time through the loop
            Utils.reap(self._kids, once=1)
            self._doperiodic()
        return len(files)

    def __onefile(self, msg, msgdata):
        # Do some common sanity checking on the message metadata.  It's got to
        # be destined for a particular mailing list.  This switchboard is used
        # to shunt off badly formatted messages.  We don't want to just trash
        # them because they may be fixable with human intervention.  Just get
        # them out of our site though.
        #
        # Find out which mailing list this message is destined for.
        listname = msgdata.get('listname')
        if not listname:
            syslog('qrunner', 'qfile metadata specifies no list: %s' %
                   filebase)
            self._shunt.enqueue(msg, metadata)
            return
        mlist = self._open_list(listname)
        if not mlist:
            syslog('qrunner',
                   'Dequeuing message destined for missing list: %s' %
                   filebase)
            self._shunt.enqueue(msg, metadata)
            return
        # Now process this message, keeping track of any subprocesses that may
        # have been spawned.  We'll reap those later.
        keepqueued = self._dispose(mlist, msg, msgdata)
        kids = msgdata.get('_kids')
        if kids:
            self._kids.update(kids)
        if keepqueued:
            self._switchboard.enqueue(msg, msgdata)
        
    # Mapping of listnames to MailList instances
    _listcache = {}

    def _open_list(self, listname, lockp=1):
        # Cache the opening of the list object given its name.  The probably
        # is only a moderate win because when a list is locked, all its
        # attributes are re-read from the config.db file.  This may help more
        # when there's a real backing database.
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

    def _log(self, exc):
        syslog('qrunner', 'Uncaught runner exception: %s' % exc)
        s = StringIO()
        traceback.print_exc(file=s)
        syslog('qrunner', s.getvalue())

    #
    # Subclasses can override _cleanup(), _dispose(), and _doperiodic()
    #
    def _cleanup(self):
        Utils.reap(self._kids)
        self._listcache.clear()

    def _dispose(self, mlist, msg, msgdata):
        raise UnimplementedError

    def _doperiodic(self):
        pass

    def _snooze(self):
        if mm_cfg.QRUNNER_SLEEP_TIME <= 0:
            return
        time.sleep(mm_cfg.QRUNNER_SLEEP_TIME)
