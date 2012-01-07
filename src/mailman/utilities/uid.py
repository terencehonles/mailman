# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

"""Unique ID generation.

Use these functions to create unique ids rather than inlining calls to hashlib
and whatnot.  These are better instrumented for testing purposes.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'UniqueIDFactory',
    'factory',
    ]


import os
import uuid
import errno

from flufl.lock import Lock

from mailman.config import config
from mailman.model.uid import UID
from mailman.testing import layers



class UniqueIDFactory:
    """A factory for unique ids."""

    def __init__(self, context=None):
        # We can't call reset() when the factory is created below, because
        # config.VAR_DIR will not be set at that time.  So initialize it at
        # the first use.
        self._uid_file = None
        self._lock_file = None
        self._lockobj = None
        self._context = context
        layers.MockAndMonkeyLayer.register_reset(self.reset)

    @property
    def _lock(self):
        if self._lockobj is None:
            # These will get automatically cleaned up by the test
            # infrastructure.
            self._uid_file = os.path.join(config.VAR_DIR, '.uid')
            if self._context:
                self._uid_file += '.' + self._context
            self._lock_file = self._uid_file + '.lock'
            self._lockobj = Lock(self._lock_file)
        return self._lockobj

    def new_uid(self):
        """Return a new UID.

        :return: The new uid
        :rtype: int
        """
        if layers.is_testing():
            # When in testing mode we want to produce predictable id, but we
            # need to coordinate this among separate processes.  We could use
            # the database, but I don't want to add schema just to handle this
            # case, and besides transactions could get aborted, causing some
            # ids to be recycled.  So we'll use a data file with a lock.  This
            # may still not be ideal due to race conditions, but I think the
            # tests will be serialized enough (and the ids reset between
            # tests) that it will not be a problem.  Maybe.
            return self._next_uid()
        while True:
            uid = uuid.uuid4()
            try:
                UID.record(uid)
            except ValueError:
                pass
            else:
                return uid

    def _next_uid(self):
        with self._lock:
            try:
                with open(self._uid_file) as fp:
                    uid = int(fp.read().strip())
                    next_uid = uid + 1
                with open(self._uid_file, 'w') as fp:
                    fp.write(str(next_uid))
                return uuid.UUID(int=uid)
            except IOError as error:
                if error.errno != errno.ENOENT:
                    raise
                with open(self._uid_file, 'w') as fp:
                    fp.write('2')
                return uuid.UUID(int=1)

    def reset(self):
        with self._lock:
            with open(self._uid_file, 'w') as fp:
                fp.write('1')



factory = UniqueIDFactory()
