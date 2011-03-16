# Copyright (C) 1998-2011 by the Free Software Foundation, Inc.
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

"""Miscellaneous essential routines.

This includes actual message transmission routines, address checking and
message and address munging, a handy-dandy routine to map a function on all
the mailing lists, and whatever else doesn't belong elsewhere.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    ]


import os
import re
import logging

# pylint: disable-msg=E0611,W0403
from string import ascii_letters, digits, whitespace

import mailman.templates


AT = '@'
CR = '\r'
DOT = '.'
EMPTYSTRING = ''
IDENTCHARS = ascii_letters + digits + '_'
NL = '\n'
UEMPTYSTRING = u''
TEMPLATE_DIR = os.path.dirname(mailman.templates.__file__)

# Search for $(identifier)s strings, except that the trailing s is optional,
# since that's a common mistake
cre = re.compile(r'%\(([_a-z]\w*?)\)s?', re.IGNORECASE)
# Search for $$, $identifier, or ${identifier}
dre = re.compile(r'(\${2})|\$([_a-z]\w*)|\${([_a-z]\w*)}', re.IGNORECASE)

log = logging.getLogger('mailman.error')



# A much more naive implementation than say, Emacs's fill-paragraph!
# pylint: disable-msg=R0912
def wrap(text, column=70, honor_leading_ws=True):
    """Wrap and fill the text to the specified column.

    Wrapping is always in effect, although if it is not possible to wrap a
    line (because some word is longer than `column' characters) the line is
    broken at the next available whitespace boundary.  Paragraphs are also
    always filled, unless honor_leading_ws is true and the line begins with
    whitespace.  This is the algorithm that the Python FAQ wizard uses, and
    seems like a good compromise.

    """
    wrapped = ''
    # first split the text into paragraphs, defined as a blank line
    paras = re.split('\n\n', text)
    for para in paras:
        # fill
        lines = []
        fillprev = False
        for line in para.split(NL):
            if not line:
                lines.append(line)
                continue
            if honor_leading_ws and line[0] in whitespace:
                fillthis = False
            else:
                fillthis = True
            if fillprev and fillthis:
                # if the previous line should be filled, then just append a
                # single space, and the rest of the current line
                lines[-1] = lines[-1].rstrip() + ' ' + line
            else:
                # no fill, i.e. retain newline
                lines.append(line)
            fillprev = fillthis
        # wrap each line
        for text in lines:
            while text:
                if len(text) <= column:
                    line = text
                    text = ''
                else:
                    bol = column
                    # find the last whitespace character
                    while bol > 0 and text[bol] not in whitespace:
                        bol -= 1
                    # now find the last non-whitespace character
                    eol = bol
                    while eol > 0 and text[eol] in whitespace:
                        eol -= 1
                    # watch out for text that's longer than the column width
                    if eol == 0:
                        # break on whitespace after column
                        eol = column
                        while eol < len(text) and text[eol] not in whitespace:
                            eol += 1
                        bol = eol
                        while bol < len(text) and text[bol] in whitespace:
                            bol += 1
                        bol -= 1
                    line = text[:eol+1] + '\n'
                    # find the next non-whitespace character
                    bol += 1
                    while bol < len(text) and text[bol] in whitespace:
                        bol += 1
                    text = text[bol:]
                wrapped += line
            wrapped += '\n'
            # end while text
        wrapped += '\n'
        # end for text in lines
    # the last two newlines are bogus
    return wrapped[:-2]
