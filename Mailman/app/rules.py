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

from Mailman.app.plugins import get_plugins



def process(mlist, msg, msgdata):
    """Default rule processing plugin.

    :param msg: The message object.
    :param msgdata: The message metadata.
    :return: A set of rule names that matched.
    """
    rule_hits = set()
    for processor_class in get_plugins('mailman.rules'):
        processor = processor_class()
        rule_hits |= processor.process(mlist, msg, msgdata)
    return rule_hits
