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

"""The built in rule set."""

__all__ = ['BuiltinRules']
__metaclass__ = type


import os
import sys

from zope.interface import implements
from Mailman.interfaces import DuplicateRuleError, IRule, IRuleSet



class BuiltinRules:
    implements(IRuleSet)

    def __init__(self):
        """The set of all built-in rules."""
        self._rules = {}
        rule_set = set()
        # Find all rules found in all modules inside our package.
        mypackage = self.__class__.__module__
        here = os.path.dirname(sys.modules[mypackage].__file__)
        for filename in os.listdir(here):
            basename, extension = os.path.splitext(filename)
            if extension <> '.py':
                continue
            module_name = mypackage + '.' + basename
            __import__(module_name, fromlist='*')
            module = sys.modules[module_name]
            for name in module.__all__:
                rule = getattr(module, name)
                if IRule.implementedBy(rule):
                    if rule.name in self._rules or rule in rule_set:
                        raise DuplicateRuleError(rule.name)
                    self._rules[rule.name] = rule
                    rule_set.add(rule)

    def __getitem__(self, rule_name):
        """See `IRuleSet`."""
        return self._rules[rule_name]()

    def get(self, rule_name, default=None):
        """See `IRuleSet`."""
        missing = object()
        rule = self._rules.get(rule_name, missing)
        if rule is missing:
            return default
        return rule()

    @property
    def rules(self):
        """See `IRuleSet`."""
        for rule in self._rules.values():
            yield rule()
