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

"""File-based logger, writes to named category files in mm_cfg.LOG_DIR."""

import sys
import os

from Mailman import mm_cfg
from Mailman.Logging.Utils import _logexc



class Logger:
    def __init__(self, category, nofail=1, immediate=0):
        """nofail says to fallback to sys.__stderr__ if write fails to
        category file - a complaint message is emitted, but no exception is
        raised.  Set nofail=0 if you want to handle the error in your code,
        instead.

        immediate=1 says to create the log file on instantiation.
        Otherwise, the file is created only when there are writes pending.
        """
        self.__filename = os.path.join(mm_cfg.LOG_DIR, category)
        self.__fp = None
        self.__nofail = nofail
        if immediate:
            self.__get_f()

    def __del__(self):
        self.close()

    def __repr__(self):
        return '<%s to %s>' % (self.__class__.__name__, `self.__filename`)

    def __get_f(self):
        if self.__fp:
            return self.__fp
        else:
            try:
                ou = os.umask(002)
                try:
                    f = self.__fp = open(self.__filename, 'a+', 1)
                finally:
                    os.umask(ou)
            except IOError, e:
                if self.__nofail:
                    _logexc(self, e)
                    f = self.__fp = sys.__stderr__
                else:
                    raise
            return f

    def flush(self):
        f = self.__get_f()
        if hasattr(f, 'flush'):
            f.flush()

    def write(self, msg):
        f = self.__get_f()
        try:
            f.write(msg)
        except IOError, msg:
            _logexc(self, msg)

    def writelines(self, lines):
        for l in lines:
            self.write(l)

    def close(self):
        if not self.__fp:
            return
        self.__get_f().close()
        self.__fp = None
