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

"""Various rule helpers"""

__all__ = [
    'initialize',
    ]

from Mailman.app.plugins import get_plugins
from Mailman.configuration import config



def initialize():
    """Find and register all rules in all plugins."""
    for rule_finder in get_plugins('mailman.rules'):
        for rule in rule_finder():
            assert rule.name not in config.rules, (
                'Duplicate rule "%s" found in %s' % (rule.name, rule_finder))
            config.rules[rule.name] = rule
