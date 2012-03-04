# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
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

"""Language manager."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'LanguageManager',
    ]

from zope.interface import implements

from mailman.interfaces.languages import ILanguageManager
from mailman.languages.language import Language



class LanguageManager:
    """Language manager."""

    implements(ILanguageManager)

    def __init__(self):
        # Mapping from 2-letter code to Language instance.
        self._languages = {}

    def add(self, code, charset, description):
        """See `ILanguageManager`."""
        if code in self._languages:
            raise ValueError('Language code already registered: ' + code)
        language = Language(code, charset, description)
        self._languages[code] = language
        return language

    @property
    def codes(self):
        """See `ILanguageManager`."""
        return iter(self._languages)

    @property
    def languages(self):
        """See `ILanguageManager`."""
        return iter(self._languages.values())

    def get(self, code, default=None):
        """See `ILanguageManager`."""
        return self._languages.get(code, default)

    def __getitem__(self, code):
        """See `ILanguageManager`."""
        return self._languages[code]

    def __contains__(self, code):
        """See `ILanguageManager`."""
        return code in self._languages

    def clear(self):
        """See `ILanguageManager`."""
        self._languages.clear()
