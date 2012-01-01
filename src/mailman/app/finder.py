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

"""Find various kinds of object in package space."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'find_components',
    'scan_module',
    ]


import os
import sys

from pkg_resources import resource_listdir



def scan_module(module, interface):
    """Return all the items in a module that conform to an interface.

    :param module: A module object.  The module's `__all__` will be scanned.
    :type module: module
    :param interface: The interface that returned objects must conform to.
    :type interface: `Interface`
    :return: The sequence of matching components.
    :rtype: objects implementing `interface`
    """
    missing = object()
    for name in module.__all__:
        component = getattr(module, name, missing)
        assert component is not missing, (
            '%s has bad __all__: %s' % (module, name))
        if interface.implementedBy(component):
            yield component


def find_components(package, interface):
    """Find components which conform to a given interface.

    Search all the modules in a given package, returning an iterator over all
    objects found that conform to the given interface.

    :param package: The package path to search.
    :type package: string
    :param interface: The interface that returned objects must conform to.
    :type interface: `Interface`
    :return: The sequence of matching components.
    :rtype: objects implementing `interface`
    """
    for filename in resource_listdir(package, ''):
        basename, extension = os.path.splitext(filename)
        if extension != '.py':
            continue
        module_name = '{0}.{1}'.format(package, basename)
        __import__(module_name, fromlist='*')
        module = sys.modules[module_name]
        if not hasattr(module, '__all__'):
            continue
        for component in scan_module(module, interface):
            yield component
