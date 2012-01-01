# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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

"""Package and module utilities."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'call_name',
    'find_name',
    ]


import sys



def find_name(dotted_name):
    """Import and return the named object in package space.

    :param dotted_name: The dotted module path name to the object.
    :type dotted_name: string
    :return: The object.
    :rtype: object
    """
    package_path, dot, object_name = dotted_name.rpartition('.')
    __import__(package_path)
    return getattr(sys.modules[package_path], object_name)


def call_name(dotted_name, *args, **kws):
    """Imports and calls the named object in package space.

    :param dotted_name: The dotted module path name to the object.
    :type dotted_name: string
    :param args: The positional arguments.
    :type args: tuple
    :param kws: The keyword arguments.
    :type kws: dict
    :return: The object.
    :rtype: object
    """
    named_callable = find_name(dotted_name)
    return named_callable(*args, **kws)
