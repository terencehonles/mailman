# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""Interface describing the basics of rules."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'IRule',
    ]


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
