# Copyright (C) 2003-2007 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

import time

from Mailman.Queue.Runner import Runner
from Mailman.Queue.Switchboard import Switchboard
from Mailman.configuration import config



class RetryRunner(Runner):
    QDIR = config.RETRYQUEUE_DIR
    SLEEPTIME = config.minutes(15)

    def __init__(self, slice=None, numslices=1):
        Runner.__init__(self, slice, numslices)
        self.__outq = Switchboard(config.OUTQUEUE_DIR)

    def _dispose(self, mlist, msg, msgdata):
        # Move it to the out queue for another retry
        self.__outq.enqueue(msg, msgdata)
        return False

    def _snooze(self, filecnt):
        # We always want to snooze
        time.sleep(float(self.SLEEPTIME))
