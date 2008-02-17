# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""The built in set of pipeline handlers."""

__metaclass__ = type
__all__ = ['initialize']


import os
import sys

from Mailman.interfaces import IHandler



def initialize():
    """Initialize the built-in handlers.

    Rules are auto-discovered by searching for IHandler implementations in all
    importable modules in this subpackage.
    """
    # Find all rules found in all modules inside our package.
    import Mailman.pipeline
    here = os.path.dirname(Mailman.pipeline.__file__)
    for filename in os.listdir(here):
        basename, extension = os.path.splitext(filename)
        if extension <> '.py':
            continue
        module_name = 'Mailman.pipeline.' + basename
        __import__(module_name, fromlist='*')
        module = sys.modules[module_name]
        for name in getattr(module, '__all__', ()):
            handler = getattr(module, name)
            if IHandler.implementedBy(handler):
                yield handler
