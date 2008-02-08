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

# A transaction wrapping decorator. The basic idea is that methods in the
# DBContext that need to operate on transaction boundaries can be written to
# be transaction naive.  By wrapping them in this decorator, they
# automatically become transaction safe.

class txn(object):
    def __init__(self, func):
        # func is a function object, not a method (even an unbound method).
        self._func = func

    def __get__(self, obj, type=None):
        # Return a wrapper function that creates a bound method from the
        # function, then calls it wrapped in a transaction boundary.  Uses a
        # non-public method called _withtxn() in the object's class.
        def wrapper(*args, **kws):
            return obj._withtxn(self._func.__get__(obj), *args, **kws)
        return wrapper
