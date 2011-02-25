# Copyright (C) 2009-2011 by the Free Software Foundation, Inc.
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

"""String utilities."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'expand',
    'oneline',
    'websafe',
    ]


import cgi
import logging

from email.errors import HeaderParseError
from email.header import decode_header, make_header
from string import Template

EMPTYSTRING = ''
UEMPTYSTRING = u''

log = logging.getLogger('mailman.error')



def expand(template, substitutions, template_class=Template):
    """Expand string template with substitutions.

    :param template: A PEP 292 $-string template.
    :type template: string
    :param substitutions: The substitutions dictionary.
    :type substitutions: dict
    :param template_class: The template class to use.
    :type template_class: class
    :return: The substituted string.
    :rtype: string
    """
    # Python 2.6 requires ** dictionaries to have str, not unicode keys, so
    # convert as necessary.  Note that string.Template uses **.  For our
    # purposes, keys should always be ascii.  Values though can be anything.
    cooked = substitutions.__class__()
    for key in substitutions:
        if isinstance(key, unicode):
            key = key.encode('ascii')
        cooked[key] = substitutions[key]
    try:
        return template_class(template).safe_substitute(cooked)
    except (TypeError, ValueError):
        # The template is really screwed up.
        log.exception('broken template: %s', template)



def oneline(s, cset='us-ascii', in_unicode=False):
    """Decode a header string in one line and convert into specified charset.

    :param s: The header string
    :type s: string
    :param cset: The character set (encoding) to use.
    :type cset: string
    :param in_unicode: Flag specifying whether to return the converted string
        as a unicode (True) or an 8-bit string (False, the default).
    :type in_unicode: bool
    :return: The decoded header string.  If an error occurs while converting
        the input string, return the string undecoded, as an 8-bit string.
    :rtype: string
    """
    try:
        h = make_header(decode_header(s))
        ustr = h.__unicode__()
        line = UEMPTYSTRING.join(ustr.splitlines())
        if in_unicode:
            return line
        else:
            return line.encode(cset, 'replace')
    except (LookupError, UnicodeError, ValueError, HeaderParseError):
        # possibly charset problem. return with undecoded string in one line.
        return EMPTYSTRING.join(s.splitlines())



def websafe(s):
    return cgi.escape(s, quote=True)
