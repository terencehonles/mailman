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

"""File-based logger, writes to named category files in mm_cfg.LOG_DIR."""

import sys
import os
import Mailman.mm_cfg
from Mailman.Logging.Utils import __logexc


class Logger:
    def __init__(self, category, nofail=1):
        """Nofail (by default) says to fallback to sys.stderr if write
        fails to category file.  A message is emitted, but the IOError is
        caught.  Set nofail=0 if you want to handle the error in your code,
        instead.
        """
        self.__filename = os.path.join(Mailman.mm_cfg.LOG_DIR, category)
	self.__fp = None
        self.__nofail = nofail

    def __del__(self):
        self.close()

    def __repr__(self):
        return '<Logger to file: %s>' % self.__filename

    def __get_f(self):
	if self.__fp:
	    return self.__fp
	else:
	    try:
		ou = os.umask(002)
		try:
		    f = self.__fp = open(self.__filename, 'a+')
		finally:
		    os.umask(ou)
	    except IOError, msg:
                if self.__nofail:
                    __logexc(self, msg)
                else:
                    # re-raise the original exception
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
            __logexc(self, msg)

    def writelines(self, lines):
	for l in lines:
	    self.write(l)

    def close(self):
	if not self.__fp:
	    return
	self.__get_f().close()
