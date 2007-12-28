# Copyright (C) 2007 by the Free Software Foundation, Inc.
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



class DuplicateRuleError(Exception):
    """A rule or rule name is added to a processor more than once."""



class IRule(Interface):
    """A basic rule."""

    name = Attribute('Rule name; must be unique.')
    description = Attribute('A brief description of the rule.')

    def check(mlist, msg, msgdata):
        """Run the rule.

        :param msg: The message object.
        :param msgdata: The message metadata.
        :return: A boolean specifying whether the rule was matched or not.
        """



class IRuleProcessor(Interface):
    """A rule processor."""

    def process(mlist, msg, msgdata):
        """Run all rules this processor knows about.

        :param mlist: The mailing list this message was posted to.
        :param msg: The message object.
        :param msgdata: The message metadata.
        :return: A set of rule names that matched.
        """

    rules = Attribute('The set of all rules this processor knows about')

    def __getitem__(rule_name):
        """Return the named rule.

        :param rule_name: The name of the rule.
        :return: The IRule given by this name.
        :raise: KeyError if no such rule is known by this processor.
        """

    def get(rule_name, default=None):
        """Return the name rule.

        :param rule_name: The name of the rule.
        :return: The IRule given by this name, or `default` if no such rule
            is known by this processor.
        """
