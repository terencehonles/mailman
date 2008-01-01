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

from munepy import Enum
from zope.interface import Interface, Attribute



class ChainJump(Enum):
    # Allow the next rule in the chain to be run.
    defer = 0
    # Jump to the 'accept' chain.
    accept = 1
    # Jump to the 'hold' chain.
    hold = 2
    # Jump to the 'reject' chain.
    reject = 3
    # Jump to the 'discard' chain.
    discard = 4



class DuplicateRuleError(Exception):
    """A rule or rule name is added to a processor more than once."""



class IRule(Interface):
    """A basic rule."""

    name = Attribute('Rule name; must be unique.')
    description = Attribute('A brief description of the rule.')

    def check(mlist, msg, msgdata):
        """Run the rule.

        The effects of running the rule can be as simple as appending the rule
        name to `msgdata['rules']` when the rule matches.  The rule is allowed
        to do other things, such as modify the message or metadata.

        :param mlist: The mailing list object.
        :param msg: The message object.
        :param msgdata: The message metadata.
        :return: A chain to jump to, i.e. an ChainJump enum.
        """



class IRuleSet(Interface):
    """A rule processor."""

    rules = Attribute('The set of all rules this processor knows about.')

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
