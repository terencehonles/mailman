# Copyright (C) 2012 by the Free Software Foundation, Inc.
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

"""The email command 'help'."""

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'Help',
    ]


from zope.interface import implements

from mailman.config import config
from mailman.core.i18n import _
from mailman.interfaces.command import ContinueProcessing, IEmailCommand
from mailman.utilities.string import wrap


SPACE = ' '



class Help:
    """The email 'help' command."""

    implements(IEmailCommand)

    name = 'help'
    argument_description = '[command]'
    description = _('Get help about available email commands.')
    short_description = description

    def process(self, mlist, msg, msgdata, arguments, results):
        """See `IEmailCommand`."""
        # With no argument, print the command and a short description, which
        # is contained in the short_description attribute.
        if len(arguments) == 0:
            length = max(len(command) for command in config.commands)
            format = '{{0: <{0}s}} - {{1}}'.format(length)
            for command_name in sorted(config.commands):
                command = config.commands[command_name]
                short_description = getattr(
                    command, 'short_description', _('n/a'))
                print(format.format(command.name, short_description), 
                      file=results)
            return ContinueProcessing.yes
        elif len(arguments) == 1:
            command_name = arguments[0]
            command = config.commands.get(command_name)
            if command is None:
                print(_('$self.name: no such command: $command_name'), 
                      file=results)
                return ContinueProcessing.no
            print('{0} {1}'.format(command.name, command.argument_description),
                  file=results)
            print(command.short_description, file=results)
            if command.short_description != command.description:
                print(wrap(command.description), file=results)
            return ContinueProcessing.yes
        else:
            printable_arguments = SPACE.join(arguments)
            print(_('$self.name: too many arguments: $printable_arguments'),
                  file=results)
            return ContinueProcessing.no
