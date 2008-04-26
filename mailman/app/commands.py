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

"""Initialize the email commands."""

__metaclass__ = type
__all__ = [
    'initialize',
    ]


from mailman.app.plugins import get_plugins
from mailman.configuration import config
from mailman.interfaces import IEmailCommand



def initialize():
    """Initialize the email commands."""
    for module in get_plugins('mailman.commands'):
        for name in module.__all__:
            command_class = getattr(module, name)
            if not IEmailCommand.implementedBy(command_class):
                continue
            assert command_class.name not in config.commands, (
                'Duplicate email command "%s" found in %s' %
                (command_class.name, module))
            config.commands[command_class.name] = command_class()
