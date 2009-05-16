# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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

"""Storm type conversions."""


from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'Enum',
    ]


import sys

from storm.properties import SimpleProperty
from storm.variables import Variable

from mailman.utilities.modules import find_name



class _EnumVariable(Variable):
    """Storm variable."""

    def parse_set(self, value, from_db):
        if value is None:
            return None
        if not from_db:
            return value
        path, colon, intvalue = value.rpartition(':')
        class_ = find_name(path)
        return class_[int(intvalue)]

    def parse_get(self, value, to_db):
        if value is None:
            return None
        if not to_db:
            return value
        return '{0}.{1}:{2}'.format(
            value.enumclass.__module__,
            value.enumclass.__name__,
            int(value))


class Enum(SimpleProperty):
    """Custom munepy.Enum type for Storm."""

    variable_class = _EnumVariable
