# Copyright (C) 2008 by the Free Software Foundation, Inc.
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

"""The built in set of pipeline handlers."""

__metaclass__ = type
__all__ = ['initialize']


import os
import sys

from mailman.interfaces import IHandler



def initialize():
    """Initialize the built-in handlers.

    Rules are auto-discovered by searching for IHandler implementations in all
    importable modules in this subpackage.
    """
    # Find all rules found in all modules inside our package.
    import mailman.pipeline
    here = os.path.dirname(mailman.pipeline.__file__)
    for filename in os.listdir(here):
        basename, extension = os.path.splitext(filename)
        if extension <> '.py':
            continue
        module_name = 'mailman.pipeline.' + basename
        __import__(module_name, fromlist='*')
        module = sys.modules[module_name]
        for name in getattr(module, '__all__', ()):
            handler = getattr(module, name)
            if IHandler.implementedBy(handler):
                yield handler
