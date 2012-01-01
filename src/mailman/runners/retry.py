# Copyright (C) 2003-2012 by the Free Software Foundation, Inc.
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

"""Retry delivery."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'RetryRunner',
    ]


import time

from mailman.config import config
from mailman.core.runner import Runner



class RetryRunner(Runner):
    """Retry delivery."""

    def _dispose(self, mlist, msg, msgdata):
        # Move the message to the out queue for another try.
        config.switchboards['out'].enqueue(msg, msgdata)
        return False

    def _snooze(self, filecnt):
        # We always want to snooze.
        time.sleep(self.sleep_float)
