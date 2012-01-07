# Copyright (C) 2006-2012 by the Free Software Foundation, Inc.
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

"""Transactional support."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'txn',
    ]


from mailman.config import config



class txn(object):
    """Decorator for transactional support.

    When the function this decorator wraps exits cleanly, the current
    transaction is committed.  When it exits uncleanly (i.e. because of an
    exception, the transaction is aborted.

    Either way, the current transaction is completed.
    """
    def __init__(self, function):
        self._function = function

    def __get__(self, obj, type=None):
        def wrapper(*args, **kws):
            try:
                rtn = self._function(obj, *args, **kws)
                config.db.commit()
                return rtn
            except:
                config.db.abort()
                raise
        return wrapper
