# Copyright (C) 2000,2001 by the Free Software Foundation, Inc.
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
from Mailman.Queue.Runner import Runner



class ArchRunner(Runner):
    def __init__(self, slice=None, numslices=1, cachelists=1):
        Runner.__init__(self, mm_cfg.ARCHQUEUE_DIR,
                        slice, numslices, cachelists)

    def _dispose(self, mlist, msg, msgdata):
        # Now try to get the list lock
        try:
            mlist.Lock(timeout=mm_cfg.LIST_LOCK_TIMEOUT)
        except LockFile.TimeOutError:
            # oh well, try again later
            return 1
        # Support clobber_date, i.e. setting the date in the archive to the
        # received date, not the (potentially bogus) Date: header of the
        # original message.  BAW: Note that there should be a third option
        # here: to clobber the date only if it's bogus, i.e. way in the future
        # or way in the past.
        if mlist.clobber_date:
            originaldate = msg['date']
            del msg['date']
            del msg['x-original-date']
            msg['Date'] = time.ctime(msgdata['received_time'])
            if originaldate:
                msg['X-Original-Date'] = originaldate
        #
        # runner specific code
        try:
            mlist.ArchiveMail(msg)
        finally:
            mlist.Save()
            mlist.Unlock()
        return 0
