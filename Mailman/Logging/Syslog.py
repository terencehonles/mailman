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

"""Central logging class for the Mailman system.

This might eventually be replaced by a syslog based logger, hence the name.
"""

from StampedLogger import StampedLogger


# global, shared logger instance
syslog = None



class Syslog:
    def __init__(self):
        self._logfiles = {}

    def __del__(self):
        self.close()

    def LogMsg(self, kind, msg):
        logf = self._logfiles.get(kind)
        if not logf:
            logf = self._logfiles[kind] = StampedLogger(kind)
        logf.write(msg + '\n')

    # For the ultimate in convenience
    __call__ = LogMsg

    def close(self):
        for kind, logger in self._logfiles.items():
            logger.close()
        self._logfiles.clear()


syslog = Syslog()
