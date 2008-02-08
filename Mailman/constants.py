# Copyright (C) 2006-2008 by the Free Software Foundation, Inc.
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

"""Various constants and enumerations."""

__all__ = [
    'SystemDefaultPreferences',
    ]


from Mailman.interfaces import DeliveryMode, DeliveryStatus, IPreferences
from zope.interface import implements



class SystemDefaultPreferences(object):
    implements(IPreferences)

    acknowledge_posts = False
    hide_address = True
    preferred_language = 'en'
    receive_list_copy = True
    receive_own_postings = True
    delivery_mode = DeliveryMode.regular
    delivery_status = DeliveryStatus.enabled
