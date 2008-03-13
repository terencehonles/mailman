# Copyright (C) 2006-2008 by the Free Software Foundation, Inc.
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

"""Transactional support."""

__metaclass__ = type
__all__ = [
    'txn',
    ]


from mailman.configuration import config



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
