# Copyright (C) 2006-2012 by the Free Software Foundation, Inc.
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

"""Various constants and enumerations."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'system_preferences',
    ]


from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.member import DeliveryMode, DeliveryStatus
from mailman.interfaces.preferences import IPreferences



class SystemDefaultPreferences:
    """The default system preferences."""

    implements(IPreferences)

    acknowledge_posts = False
    hide_address = True
    receive_list_copy = True
    receive_own_postings = True
    delivery_mode = DeliveryMode.regular
    delivery_status = DeliveryStatus.enabled

    @property
    def preferred_language(self):
        """Return the system preferred language."""
        return getUtility(ILanguageManager)[config.mailman.default_language]



system_preferences = SystemDefaultPreferences()
