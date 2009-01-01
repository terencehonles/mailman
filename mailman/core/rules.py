# Copyright (C) 2007-2009 by the Free Software Foundation, Inc.
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

"""Various rule helpers"""

__metaclass__ = type
__all__ = [
    'initialize',
    ]


from zope.interface import implements
from zope.interface.verify import verifyObject

from mailman.config import config
from mailman.core.plugins import get_plugins
from mailman.interfaces import IRule



def initialize():
    """Find and register all rules in all plugins."""
    # Find rules in plugins.
    for rule_finder in get_plugins('mailman.rules'):
        for rule_class in rule_finder():
            rule = rule_class()
            verifyObject(IRule, rule)
            assert rule.name not in config.rules, (
                'Duplicate rule "%s" found in %s' % (rule.name, rule_finder))
            config.rules[rule.name] = rule
