# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

"""Interface describing the basics of rules."""

from zope.interface import Interface, Attribute



class IRule(Interface):
    """A basic rule."""

    name = Attribute('Rule name; must be unique.')

    description = Attribute('A brief description of the rule.')

    record = Attribute(
        """Should this rule's success or failure be recorded?

        This is a boolean; if True then this rule's hit or miss will be
        recorded in a message header.  If False, it won't.
        """)

    def check(mlist, msg, msgdata):
        """Run the rule.

        :param mlist: The mailing list object.
        :param msg: The message object.
        :param msgdata: The message metadata.
        :returns: a boolean specifying whether the rule matched or not.
        """
