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

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'dbconnection',
    'transaction',
    'transactional',
    ]


from contextlib import contextmanager

from mailman.config import config



@contextmanager
def transaction():
    """Context manager for ensuring the transaction is complete."""
    try:
        yield
    except:
        config.db.abort()
        raise
    else:
        config.db.commit()



def transactional(function):
    """Decorator for transactional support.

    When the function this decorator wraps exits cleanly, the current
    transaction is committed.  When it exits uncleanly (i.e. because of an
    exception, the transaction is aborted.

    Either way, the current transaction is completed.
    """
    def wrapper(*args, **kws):
        try:
            rtn = function(*args, **kws)
            config.db.commit()
            return rtn
        except:
            config.db.abort()
            raise
    return wrapper



def dbconnection(function):
    """Decorator for getting at the database connection.

    Use this to avoid having to access the global `config.db.store`
    attribute.  This calls the function with `store` as the first argument.
    """
    def wrapper(*args, **kws):
        # args[0] is self.
        return function(args[0], config.db.store, *args[1:], **kws)
    return wrapper
