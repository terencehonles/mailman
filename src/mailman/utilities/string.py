# Copyright (C) 2009-2012 by the Free Software Foundation, Inc.
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
    'uncanonstr',
    'websafe',
    'wrap',
    ]


import cgi
import logging

from email.errors import HeaderParseError
from email.header import decode_header, make_header
from string import Template, whitespace
from textwrap import TextWrapper, dedent
from zope.component import getUtility

from mailman.interfaces.languages import ILanguageManager


EMPTYSTRING = ''
NL = '\n'

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
        line = EMPTYSTRING.join(ustr.splitlines())
        if in_unicode:
            return line
        else:
            return line.encode(cset, 'replace')
    except (LookupError, UnicodeError, ValueError, HeaderParseError):
        # possibly charset problem. return with undecoded string in one line.
        return EMPTYSTRING.join(s.splitlines())



def websafe(s):
    return cgi.escape(s, quote=True)



# The opposite of canonstr() -- sorta.  I.e. it attempts to encode s in the
# charset of the given language, which is the character set that the page will
# be rendered in, and failing that, replaces non-ASCII characters with their
# html references.  It always returns a byte string.
def uncanonstr(s, lang=None):
    if s is None:
        s = u''
    if lang is None:
        charset = 'us-ascii'
    else:
        charset = getUtility(ILanguageManager)[lang].charset
    # See if the string contains characters only in the desired character
    # set.  If so, return it unchanged, except for coercing it to a byte
    # string.
    try:
        if isinstance(s, unicode):
            return s.encode(charset)
        else:
            unicode(s, charset)
            return s
    except UnicodeError:
        # Nope, it contains funny characters, so html-ref it
        a = []
        for c in s:
            o = ord(c)
            if o > 127:
                a.append('&#%3d;' % o)
            else:
                a.append(c)
        # Join characters together and coerce to byte string
        return str(EMPTYSTRING.join(a))



def wrap(text, column=70, honor_leading_ws=True):
    """Wrap and fill the text to the specified column.

    The input text is wrapped and filled as done by the standard library
    textwrap module.  The differences here being that this function is capable
    of filling multiple paragraphs (as defined by text separated by blank
    lines).  Also, when `honor_leading_ws` is True (the default), paragraphs
    that being with whitespace are not wrapped.  This is the algorithm that
    the Python FAQ wizard used.
    """
    # First, split the original text into paragraph, keeping all blank lines
    # between them.
    paragraphs = []
    paragraph = []
    last_indented = False
    for line in text.splitlines(True):
        is_indented = (len(line) > 0 and line[0] in whitespace)
        if line == NL:
            if len(paragraph) > 0:
                paragraphs.append(EMPTYSTRING.join(paragraph))
            paragraphs.append(line)
            last_indented = False
            paragraph = []
        elif last_indented != is_indented:
            # The indentation level changed.  We treat this as a paragraph
            # break but no blank line will be issued between paragraphs.
            if len(paragraph) > 0:
                paragraphs.append(EMPTYSTRING.join(paragraph))
            # The next paragraph starts with this line.
            paragraph = [line]
            last_indented = is_indented
        else:
            # This line does not constitute a paragraph break.
            paragraph.append(line)
    # We've consumed all the lines in the original text.  Transfer the last
    # paragraph we were collecting to the full set of paragraphs.
    paragraphs.append(EMPTYSTRING.join(paragraph))
    # Now iterate through all paragraphs, wrapping as necessary.
    wrapped_paragraphs = []
    # The dedented wrapper.
    wrapper = TextWrapper(width=column,
                          fix_sentence_endings=True)
    # The indented wrapper.  For this one, we'll clobber initial_indent and
    # subsequent_indent as needed per indented chunk of text.
    iwrapper = TextWrapper(width=column,
                           fix_sentence_endings=True,
                           )
    add_paragraph_break = False
    for paragraph in paragraphs:
        if add_paragraph_break:
            wrapped_paragraphs.append(NL)
            add_paragraph_break = False
        paragraph_text = EMPTYSTRING.join(paragraph)
        # Just copy the blank lines to the final set of paragraphs.
        if len(paragraph) == 0 or paragraph == NL:
            wrapped_paragraphs.append(NL)
        # Choose the wrapper based on whether the paragraph is indented or
        # not.  Also, do not wrap indented paragraphs if honor_leading_ws is
        # set.
        elif paragraph[0] in whitespace:
            if honor_leading_ws:
                # Leave the indented paragraph verbatim.
                wrapped_paragraphs.append(paragraph_text)
            else:
                # The paragraph should be wrapped, but it must first be
                # dedented.  The leading whitespace on the first line of the
                # original text will be used as the indentation for all lines
                # in the wrapped text.
                for i, ch in enumerate(paragraph_text):
                    if ch not in whitespace:
                        break
                leading_ws = paragraph[:i]
                iwrapper.initial_indent=leading_ws
                iwrapper.subsequent_indent=leading_ws
                paragraph_text = dedent(paragraph_text)
                wrapped_paragraphs.append(iwrapper.fill(paragraph_text))
                add_paragraph_break = True
        else:
            # Fill this paragraph.  fill() consumes the trailing newline.
            wrapped_paragraphs.append(wrapper.fill(paragraph_text))
            add_paragraph_break = True
    return EMPTYSTRING.join(wrapped_paragraphs)
