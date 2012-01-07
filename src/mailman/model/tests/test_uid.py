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

"""Test the UID model class."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import uuid
import unittest

from mailman.model.uid import UID
from mailman.testing.layers import ConfigLayer



class TestUID(unittest.TestCase):
    layer = ConfigLayer

    def test_record(self):
        # Test that the .record() method works.
        UID.record(uuid.UUID(int=11))
        UID.record(uuid.UUID(int=99))
        self.assertRaises(ValueError, UID.record, uuid.UUID(int=11))

    def test_longs(self):
        # In a non-test environment, the uuid will be a long int.
        my_uuid = uuid.uuid4()
        UID.record(my_uuid)
        self.assertRaises(ValueError, UID.record, my_uuid)
