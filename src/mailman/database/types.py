# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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


from storm.properties import SimpleProperty
from storm.variables import Variable



class _EnumVariable(Variable):
    """Storm variable for supporting flufl.enum.Enum types.

    To use this, make the database column a INTEGER.
    """

    def __init__(self, *args, **kws):
        self._enum = kws.pop('enum')
        super(_EnumVariable, self).__init__(*args, **kws)

    def parse_set(self, value, from_db):
        if value is None:
            return None
        if not from_db:
            return value
        return self._enum[value]

    def parse_get(self, value, to_db):
        if value is None:
            return None
        if not to_db:
            return value
        return int(value)


class Enum(SimpleProperty):
    """Custom Enum type for Storm supporting flufl.enum.Enums."""

    variable_class = _EnumVariable

    def __init__(self, enum=None):
        super(Enum, self).__init__(enum=enum)
