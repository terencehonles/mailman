# Copyright (C) 2008-2012 by the Free Software Foundation, Inc.
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

"""Interfaces defining email commands."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ContinueProcessing',
    'ICLISubCommand',
    'IEmailCommand',
    'IEmailResults',
    ]


from flufl.enum import Enum
from zope.interface import Interface, Attribute



class ContinueProcessing(Enum):
    """Should `IEmailCommand.process()` continue or not."""
    no = 0
    yes = 1



class IEmailResults(Interface):
    """The email command results object."""

    output = Attribute('An output file object for printing results to.')



class IEmailCommand(Interface):
    """An email command."""

    name = Attribute('Command name as seen in a -request email.')

    argument_description = Attribute('Description of command arguments.')

    description = Attribute('Command help.')

    def process(mlist, msg, msgdata, arguments, results):
        """Process the email command.

        :param mlist: The mailing list target of the command.
        :param msg: The original message object.
        :param msgdata: The message metadata.
        :param arguments: The command arguments tuple.
        :param results: An IEmailResults object for these commands.
        :return: A `ContinueProcessing` enum specifying whether to continue
            processing or not.
        """



class ICLISubCommand(Interface):
    """A command line interface subcommand."""

    name = Attribute('The command name; must be unique')

    __doc__ = Attribute('The command short help')

    def add(parser, command_parser):
        """Add the subcommand to the subparser.

        :param parser: The argument parser.
        :type parser: `argparse.ArgumentParser`
        :param subparser: The command subparser.
        :type subparser: `argparse.ArgumentParser`
        """

    def process(args):
        """Process the subcommand.

        :param args: The namespace, as passed in by argparse.
        :type args: `argparse.Namespace`
        """
