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

"""Style manager."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'StyleManager',
    ]


from operator import attrgetter
from zope.interface import implements
from zope.interface.verify import verifyObject

from mailman.interfaces.styles import (
    DuplicateStyleError, IStyle, IStyleManager)
from mailman.utilities.modules import call_name



class StyleManager:
    """The built-in style manager."""

    implements(IStyleManager)

    def __init__(self):
        """Install all styles from the configuration files."""
        self._styles = {}

    def populate(self):
        self._styles.clear()
        # Avoid circular imports.
        from mailman.config import config
        # Install all the styles described by the configuration files.
        for section in config.style_configs:
            class_path = section['class']
            style = call_name(class_path)
            assert section.name.startswith('style'), (
                'Bad style section name: %s' % section.name)
            style.name = section.name[6:]
            style.priority = int(section.priority)
            self.register(style)

    def get(self, name):
        """See `IStyleManager`."""
        return self._styles.get(name)

    def lookup(self, mailing_list):
        """See `IStyleManager`."""
        matched_styles = []
        for style in self.styles:
            style.match(mailing_list, matched_styles)
        for style in matched_styles:
            yield style

    @property
    def styles(self):
        """See `IStyleManager`."""
        for style in sorted(self._styles.values(),
                            key=attrgetter('priority'),
                            reverse=True):
            yield style

    def register(self, style):
        """See `IStyleManager`."""
        verifyObject(IStyle, style)
        if style.name in self._styles:
            raise DuplicateStyleError(style.name)
        self._styles[style.name] = style

    def unregister(self, style):
        """See `IStyleManager`."""
        # Let KeyErrors percolate up.
        del self._styles[style.name]
