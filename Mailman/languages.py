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

"""Language manager."""

from zope.interface import implements
from Mailman.interfaces import ILanguageManager



class LanguageManager:
    implements(ILanguageManager)

    def __init__(self):
        self._language_data = {}
        self._enabled = set()

    def add_language(self, code, description, charset, enable=True):
        self._language_data[code] = (description, charset)
        if enable:
            self._enabled.add(code)

    def enable_language(self, code):
        # As per the interface, let KeyError percolate up.
        self._language_data[code]
        self._enabled.add(code)

    def get_description(self, code):
        return self._language_data[code][0]

    def get_charset(self, code):
        return self._language_data[code][1]

    @property
    def known_codes(self):
        return iter(self._language_data)

    @property
    def enabled_codes(self):
        return iter(self._enabled)

    @property
    def enabled_names(self):
        for code in self._enabled:
            description, charset = self._language_data[code]
            yield description
