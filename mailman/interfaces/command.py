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

"""Interfaces defining email commands."""

from zope.interface import Interface, Attribute



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
        :return: True if further processing should be taken of the email
            commands in this message.
        """
