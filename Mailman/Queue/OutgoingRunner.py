#! /usr/bin/env python
#
# Copyright (C) 2000 by the Free Software Foundation, Inc.
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

"""Outgoing queue runner."""

from Mailman import mm_cfg
from Mailman.Queue import Runner
from Mailman.Handlers import HandlerAPI



class OutgoingRunner(Runner.Runner):
    def __init__(self, cachelists=1):
        Runner.Runner.__init__(self, mm_cfg.OUTQUEUE_DIR)

    def _dispose_message(self, msg, msgdata):
        # TBD: refactor this stanza.
        # Find out which mailing list this message is destined for
        listname = msgdata.get('listname')
        if not listname:
            syslog('qrunner', 'qfile metadata specifies no list: %s' % root)
            return 1
        mlist = self._open_list(listname)
        if not mlist:
            syslog('qrunner',
                   'Dequeuing message destined for missing list: %s' % root)
            self._dequeue(root)
            return 1
        # Now try to get the list lock
        try:
            mlist.Lock(timeout=mm_cfg.LIST_LOCK_TIMEOUT)
        except LockFile.TimeOutError:
            # oh well, try again later
            return 1
        #
        # runner specific code
        try:
            msgdata['pipeline'] = [mm_cfg.DELIVERY_MODULE]
            return HandlerAPI.DeliverToList(mlist, msg, msgdata)
        finally:
            mlist.Save()
            mlist.Unlock()
