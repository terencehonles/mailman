# Copyright (C) 2011 by the Free Software Foundation, Inc.
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
import time
import hashlib

from mailman.testing.layers import MockAndMonkeyLayer
from mailman.utilities.passwords import SALT_LENGTH



class UniqueIDFactory:
    """A factory for unique ids."""

    # The predictable id.
    predictable_id = None

    def new_uid(self, bytes=None):
        if MockAndMonkeyLayer.testing_mode:
            uid = self.predictable_id
            self.predictable_id += 1
            return unicode(uid)
        salt = os.urandom(SALT_LENGTH)
        h = hashlib.sha1(repr(time.time()))
        h.update(salt)
        if bytes is not None:
            h.update(bytes)
        return unicode(h.hexdigest(), 'us-ascii')

    def reset(self):
        self.predictable_id = 1



factory = UniqueIDFactory()
factory.reset()
MockAndMonkeyLayer.register_reset(factory.reset)
