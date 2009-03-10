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

"""The built in rule set."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'builtin_rules',
    ]


import os
import sys

from mailman.interfaces.rules import IRule



def builtin_rules():
    """Return the built-in rules.

    Rules are auto-discovered by searching for IRule implementations in all
    importable modules in this subpackage.
    """
    # Find all rules found in all modules inside our package.
    import mailman.rules
    here = os.path.dirname(mailman.rules.__file__)
    for filename in os.listdir(here):
        basename, extension = os.path.splitext(filename)
        if extension <> '.py':
            continue
        module_name = 'mailman.rules.' + basename
        __import__(module_name, fromlist='*')
        module = sys.modules[module_name]
        for name in module.__all__:
            rule = getattr(module, name)
            if IRule.implementedBy(rule):
                yield rule
