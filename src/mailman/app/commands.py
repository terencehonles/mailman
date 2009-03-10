# Copyright (C) 2008-2009 by the Free Software Foundation, Inc.
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

"""Initialize the email commands."""

from __future__ import unicode_literals

__metaclass__ = type
__all__ = [
    'initialize',
    ]


import sys

from mailman import commands
from mailman.config import config
from mailman.interfaces.command import IEmailCommand



def initialize():
    """Initialize the email commands."""
    for command_module in commands.__all__:
        module_name = 'mailman.commands.' + command_module
        __import__(module_name)
        module = sys.modules[module_name]
        for name in dir(module):
            command_class = getattr(module, name)
            try:
                is_command = IEmailCommand.implementedBy(command_class)
            except TypeError:
                is_command = False
            if not is_command:
                continue
            assert command_class.name not in config.commands, (
                'Duplicate email command "{0}" found in {1}'.format(
                    command_class.name, module))
            config.commands[command_class.name] = command_class()
