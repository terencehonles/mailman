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

"""Interfaces for managing languages."""

from zope.interface import Interface, Attribute



class ILanguageManager(Interface):
    """A language manager.

    Current, disabling languages is not supported.
    """

    def add_language(code, description, charset, enable=True):
        """Teach the language manager about a language.

        :param code: The short two-character language code for the
            language.  If the language manager already knows about this code,
            the old language binding is lost.
        :param description: The English description of the language,
            e.g. 'English' or 'French'.
        :param charset: The character set that the language uses,
            e.g. 'us-ascii', 'iso-8859-1', or 'utf-8'
        :param enable: Enable the language at the same time.
        """

    def enable_language(code):
        """Enable a language that the manager already knows about.

        :raises KeyError: when the manager does not know about the given
            language code.
        """

    def get_language_data(code):
        """Return the description and charset for the given `code`.

        :param code: The code to lookup.
        :returns: A 2-tuple of the description and charset for the code.
        :raises KeyError: when the code is unknown.
        """

    known_codes = Attribute(
        """An iterator over all known codes.""")

    enabled_codes = Attribute(
        """An iterator over all enabled codes.""")

    enabled_names = Attribute(
        """An iterator over all enabled language names.""")
