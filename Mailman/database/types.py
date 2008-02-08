# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

__all__ = [
    'Enum',
    ]


import sys

from storm.properties import SimpleProperty
from storm.variables import UnicodeVariable, Variable



class _EnumVariable(Variable):
    """Storm variable."""

    def parse_set(self, value, from_db):
        if value is None:
            return None
        if not from_db:
            return value
        path, intvalue = value.rsplit(':', 1)
        modulename, classname = path.rsplit('.', 1)
        __import__(modulename)
        cls = getattr(sys.modules[modulename], classname)
        return cls[int(intvalue)]

    def parse_get(self, value, to_db):
        if value is None:
            return None
        if not to_db:
            return value
        return '%s.%s:%d' % (value.enumclass.__module__,
                             value.enumclass.__name__,
                             int(value))


class Enum(SimpleProperty):
    """Custom munepy.Enum type for Storm."""

    variable_class = _EnumVariable
