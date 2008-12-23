# Copyright (C) 2003-2008 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

import time

from mailman.config import config
from mailman.queue import Runner, Switchboard



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
