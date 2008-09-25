# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

    def get_description(code):
        """Return the language description for the given code.

        :param code: The two letter language code to look up.
        :returns: The English description of the language.
        :raises KeyError: when the code has not been added.
        """

    def get_charset(code):
        """Return the character set for the given code.

        :param code: The two letter language code to look up.
        :returns: The character set of the language.
        :raises KeyError: when the code has not been added.
        """

    known_codes = Attribute(
        """An iterator over all known codes.""")

    enabled_codes = Attribute(
        """An iterator over all enabled codes.""")

    enabled_names = Attribute(
        """An iterator over all enabled language names.""")



class ILanguage(Interface):
    """The representation of a language."""

    code = Attribute("""The 2-character language code.""")
