# Copyright (C) 2011-2012 by the Free Software Foundation, Inc.
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

from __future__ import absolute_import, print_function, unicode_literals

__metaclass__ = type
__all__ = [
    'TemplateNotFoundError',
    'find',
    'make',
    'search',
    ]


import os
import sys
import errno

from itertools import product
from pkg_resources import resource_filename

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



def search(template_file, mlist=None, language=None):
    """Generator that provides file system search order.

    This is Mailman's internal template search algorithm.  The first locations
    searched are within the $template_dir directory, allowing a site to
    override a template for a specific mailing list, all the mailing lists in
    a domain, or site-wide.

    The <language> path component is variable, and described below.

    * The list-specific language directory
      $template_dir/lists/<mlist.fqdn_listname>/<language>

    * The domain-specific language directory
      $template_dir/domains/<mlist.mail_host>/<language>

    * The site-wide language directory
      $template_dir/site/<language>

    The <language> path component is calculated as follows, in this order:

    * The `language` parameter if given
    * `mlist.preferred_language` if given
    * The server's default language
    * English ('en')

    Languages are iterated after each of the four locations are searched.  So
    for example, when searching for the 'foo.txt' template, where the server's
    default language is 'fr', the mailing list's (test@example.com) language
    is 'de' and the `language` parameter is 'it', these locations are searched
    in order:

    * $template_dir/lists/test@example.com/it/foo.txt
    * $template_dir/domains/example.com/it/foo.txt
    * $template_dir/site/it/foo.txt

    * $template_dir/lists/test@example.com/de/foo.txt
    * $template_dir/domains/example.com/de/foo.txt
    * $template_dir/site/de/foo.txt

    * $template_dir/lists/test@example.com/fr/foo.txt
    * $template_dir/domains/example.com/fr/foo.txt
    * $template_dir/site/fr/foo.txt

    * $template_dir/lists/test@example.com/en/foo.txt
    * $template_dir/domains/example.com/en/foo.txt
    * $template_dir/site/en/foo.txt

    After all those paths are searched, the final fallback is the English
    template within the Mailman source tree.

    * <source_dir>/templates/en/foo.txt
    """
    # The languages in search order.
    languages = ['en', system_preferences.preferred_language.code]
    if mlist is not None:
        languages.append(mlist.preferred_language.code)
    if language is not None:
        languages.append(language)
    languages.reverse()
    # The non-language qualified $template_dir paths in search order.
    paths = [os.path.join(config.TEMPLATE_DIR, 'site')]
    if mlist is not None:
        paths.append(os.path.join(
            config.TEMPLATE_DIR, 'domains', mlist.mail_host))
        paths.append(os.path.join(
            config.TEMPLATE_DIR, 'lists', mlist.fqdn_listname))
    paths.reverse()
    for language, path in product(languages, paths):
        yield os.path.join(path, language, template_file)
    # Finally, fallback to the in-tree English template.
    templates_dir = resource_filename('mailman', 'templates')
    yield os.path.join(templates_dir, 'en', template_file)



def find(template_file, mlist=None, language=None, _trace=False):
    """Use Mailman's internal template search order to find a template.

    :param template_file: The name of the template file to search for.
    :type template_file: string
    :param mlist: Optional mailing list used as the context for
        searching for the template file.  The list's preferred language will
        influence the search, as will the list's data directory.
    :type mlist: `IMailingList`
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
    raw_search_order = search(template_file, mlist, language)
    for path in raw_search_order:
        try:
            if _trace:
                print('@@@', path, end='', file=sys.stderr)
            fp = open(path)
        except IOError as error:
            if error.errno == errno.ENOENT:
                if _trace:
                    print('MISSING', file=sys.stderr)
            else:
                raise
        else:
            if _trace:
                print('FOUND:', path, file=sys.stderr)
            return path, fp
    raise TemplateNotFoundError(template_file)


def make(template_file, mlist=None, language=None, wrap=True,
         _trace=False, **kw):
    """Locate and 'make' a template file.

    The template file is located as with `find()`, and the resulting text is
    optionally wrapped and interpolated with the keyword argument dictionary.

    :param template_file: The name of the template file to search for.
    :type template_file: string
    :param mlist: Optional mailing list used as the context for
        searching for the template file.  The list's preferred language will
        influence the search, as will the list's data directory.
    :type mlist: `IMailingList`
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
    path, fp = find(template_file, mlist, language, _trace)
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
