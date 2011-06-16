# Copyright (C) 2011 by the Free Software Foundation, Inc.
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

"""i18n template search and interpolation."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'TemplateNotFoundError',
    'find',
    'make',
    ]


import os
import sys
import errno

from itertools import product

from mailman.config import config
from mailman.core.constants import system_preferences
from mailman.core.errors import MailmanException
from mailman.core.i18n import _
from mailman.utilities.string import expand, wrap as wrap_text



class TemplateNotFoundError(MailmanException):
    """The named template was not found."""

    def __init__(self, template_file):
        self.template_file = template_file

    def __str__(self):
        return self.template_file



def _search(template_file, mailing_list=None, language=None):
    """Generator that provides file system search order."""

    languages = ['en', system_preferences.preferred_language.code]
    if mailing_list is not None:
        languages.append(mailing_list.preferred_language.code)
    if language is not None:
        languages.append(language)
    languages.reverse()
    # File system locations to search.
    paths = [config.TEMPLATE_DIR,
             os.path.join(config.TEMPLATE_DIR, 'site')]
    if mailing_list is not None:
        paths.append(os.path.join(config.TEMPLATE_DIR,
                                  mailing_list.mail_host))
        paths.append(os.path.join(config.LIST_DATA_DIR,
                                  mailing_list.fqdn_listname))
    paths.reverse()
    for language, path in product(languages, paths):
        yield os.path.join(path, language, template_file)



def find(template_file, mailing_list=None, language=None, _trace=False):
    """Locate an i18n template file.

    When something in Mailman needs a template file, it always asks for the
    file through this interface.  The results of the search is path to the
    'matching' template, with the search order depending on whether
    `mailing_list` and `language` are provided.

    When looking for a template in a specific language, there are 4 locations
    that are searched, in this order:

    * The list-specific language directory
      <var_dir>/lists/<fqdn_listname>/<language>

    * The domain-specific language directory
      <template_dir>/<list-host-name>/<language>

    * The site-wide language directory
      <template_dir>/site/<language>

    * The global default language directory
      <template_dir>/<language>

    The first match stops the search.  In this way, you can specialize
    templates at the desired level, or if you only use the default templates,
    you don't need to change anything.  NEVER modify files in
    <template_dir>/<language> since Mailman will overwrite these when you
    upgrade.  Instead you can use <template_dir>/site.

    The <language> path component is calculated as follows, in this order:

    * The `language` parameter if given
    * `mailing_list.preferred_language` if given
    * The server's default language
    * English ('en')

    Languages are iterated after each of the four locations are searched.  So
    for example, when searching for the 'foo.txt' template, where the server's
    default language is 'fr', the mailing list's (test@example.com) language
    is 'de' and the `language` parameter is 'it', these locations are searched
    in order:

    * <var_dir>/lists/test@example.com/it/foo.txt
    * <template_dir>/example.com/it/foo.txt
    * <template_dir>/site/it/foo.txt
    * <template_dir>/it/foo.txt

    * <var_dir>/lists/test@example.com/de/foo.txt
    * <template_dir>/example.com/de/foo.txt
    * <template_dir>/site/de/foo.txt
    * <template_dir>/de/foo.txt

    * <var_dir>/lists/test@example.com/fr/foo.txt
    * <template_dir>/example.com/fr/foo.txt
    * <template_dir>/site/fr/foo.txt
    * <template_dir>/fr/foo.txt

    * <var_dir>/lists/test@example.com/en/foo.txt
    * <template_dir>/example.com/en/foo.txt
    * <template_dir>/site/en/foo.txt
    * <template_dir>/en/foo.txt

    :param template_file: The name of the template file to search for.
    :type template_file: string
    :param mailing_list: Optional mailing list used as the context for
        searching for the template file.  The list's preferred language will
        influence the search, as will the list's data directory.
    :type mailing_list: `IMailingList`
    :param language: Optional language code, which influences the search.
    :type language: string
    :param _trace: Enable printing of debugging information during
        template search.
    :type _trace: bool
    :return: A tuple of the file system path to the first matching template,
        and an open file object allowing reading of the file.
    :rtype: (string, file)
    :raises TemplateNotFoundError: when the template could not be found.
    """
    raw_search_order = _search(template_file, mailing_list, language)
    for path in raw_search_order:
        try:
            if _trace:
                print >> sys.stderr, '@@@', path,
            fp = open(path)
        except IOError as error:
            if error.errno == errno.ENOENT:
                if _trace:
                    print >> sys.stderr, 'MISSING'
            else:
                raise
        else:
            if _trace:
                print >> sys.stderr, 'FOUND:', path
            return path, fp
    raise TemplateNotFoundError(template_file)


def make(template_file, mailing_list=None, language=None, wrap=True,
         _trace=False, **kw):
    """Locate and 'make' a template file.

    The template file is located as with `find()`, and the resulting text is
    optionally wrapped and interpolated with the keyword argument dictionary.

    :param template_file: The name of the template file to search for.
    :type template_file: string
    :param mailing_list: Optional mailing list used as the context for
        searching for the template file.  The list's preferred language will
        influence the search, as will the list's data directory.
    :type mailing_list: `IMailingList`
    :param language: Optional language code, which influences the search.
    :type language: string
    :param wrap: When True, wrap the text.
    :type wrap: bool
    :param _trace: Passed through to ``find()``, this enables printing of
        debugging information during template search.
    :type _trace: bool
    :param **kw: Keyword arguments for template interpolation.
    :return: The interpolated text.
    :rtype: string
    :raises TemplateNotFoundError: when the template could not be found.
    """
    path, fp = find(template_file, mailing_list, language, _trace)
    try:
        # XXX Removing the trailing newline is a hack carried over from
        # Mailman 2.  The (stripped) template text is then passed through the
        # translation catalog.  This ensures that the translated text is
        # unicode, and also allows for volunteers to translate the templates
        # into the language catalogs.
        template = _(fp.read()[:-1])
    finally:
        fp.close()
    assert isinstance(template, unicode), 'Translated template is not unicode'
    text = expand(template, kw)
    if wrap:
        return wrap_text(text)
    return text
