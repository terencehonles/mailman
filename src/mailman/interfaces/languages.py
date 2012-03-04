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

"""Interfaces for managing languages."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'ILanguage',
    'ILanguageManager',
    ]


from zope.interface import Interface, Attribute



class ILanguage(Interface):
    """The representation of a language."""

    code = Attribute('The 2-character language code.')

    charset = Attribute('The character set or encoding for this language.')

    description = Attribute("The language's description.")



class ILanguageManager(Interface):
    """A language manager.

    Current, disabling languages is not supported.
    """

    def add(code, charset, description):
        """Teach the language manager about a language.

        :param code: The short two-character language code for the
            language.  If the language manager already knows about this code,
            the old language binding is lost.
        :type code: string
        :param charset: The character set that the language uses,
            e.g. 'us-ascii', 'iso-8859-1', or 'utf-8'
        :type charset: string
        :param description: The English description of the language,
            e.g. 'English' or 'French'.
        :type description: string
        :return: The language object just added.
        :rtype: ILanguage
        """

    codes = Attribute('An iterator over all known codes.')

    languages = Attribute('An iterator of all the languages.')

    def __getitem__(code):
        """Return the language associated with the language code.

        :param code: The 2-letter language code.
        :type code: string
        :return: The language instance.
        :rtype: `ILanguage`
        :raises KeyError: if code is not associated with a known language.
        """

    def get(code, default=None):
        """Return the language associated with the language code.

        :param code: The 2-letter language code.
        :type code: string
        :param default: The value to return if the code is not known.
        :type default: anything
        :return: The language instance or `default`.
        :rtype: `ILanguage` or `default`
        """

    def __contains__(code):
        """True if the language code is known.

        :return: A flag indicating whether the language code is known or not.
        :rtype: bool
        """

    def clear():
        """Remove all language code mappings."""
