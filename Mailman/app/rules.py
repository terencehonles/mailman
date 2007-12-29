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

"""Process all rules defined by entry points."""

__all__ = [
    'find_rule',
    'process',
    ]

from Mailman.app.plugins import get_plugins



def process(mlist, msg, msgdata, rule_set=None):
    """Default rule processing plugin.

    Rules are processed in random order.

    :param msg: The message object.
    :param msgdata: The message metadata.
    :param rule_set: The name of the rules to run.  None (the default) means
        to run all available rules.
    :return: A set of rule names that matched.
    """
    # Collect all rules from all rule processors.
    rules = set()
    for rule_set_class in get_plugins('mailman.rules'):
        rules |= set(rule for rule in rule_set_class().rules
                     if rule_set is None or rule.name in rule_set)
    # Now process all rules, returning the set of rules that match.
    rule_matches = set()
    for rule in rules:
        if rule.check(mlist, msg, msgdata):
            rule_matches.add(rule.name)
    return rule_matches



def find_rule(rule_name):
    """Find the named rule.

    :param rule_name: The name of the rule to find.
    :return: The named rule, or None if no such rule exists.
    """
    for rule_set_class in get_plugins('mailman.rules'):
        rule = rule_set_class().get(rule_name)
        if rule is not None:
            return rule
    return None
