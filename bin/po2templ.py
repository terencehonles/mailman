#! @PYTHON@
#
# Copyright (C) 2005-2006 by the Free Software Foundation, Inc.
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

# Author: Tokio Kikuchi <tkikuchi@is.kochi-u.ac.jp>


"""po2templ.py

Extract templates from language po file.

Usage: po2templ.py languages
"""

import re
import sys

cre = re.compile('^#:\s*templates/en/(?P<filename>.*?):1')



def do_lang(lang):
    in_template = False
    in_msg = False
    msgstr = ''
    fp = file('messages/%s/LC_MESSAGES/mailman.po' % lang)
    try:
        for line in fp:
            m = cre.search(line)
            if m:
                in_template = True
                in_msg = False
                filename = m.group('filename')
                outfilename = 'templates/%s/%s' % (lang, filename)
                continue
            if in_template and line.startswith('#,'):
                if line.strip() == '#, fuzzy':
                    in_template = False
                continue
            if in_template and line.startswith('msgstr'):
                line = line[7:]
                in_msg = True
            if in_msg:
                if not line.strip():
                    in_template = False
                    in_msg = False
                    if len(msgstr) > 1 and outfilename:
                        # exclude no translation ... 1 is for LF only
                        outfile = file(outfilename, 'w')
                        try:
                            outfile.write(msgstr)
                            outfile.write('\n')
                        finally:
                            outfile.close()
                    outfilename = ''
                    msgstr = ''
                    continue
                msgstr += eval(line)
    finally:
        fp.close()
    if len(msgstr) > 1 and outfilename:
        # flush remaining msgstr (last template file)
        outfile = file(outfilename, 'w')
        try:
            outfile.write(msgstr)
            outfile.write('\n')
        finally:
            outfile.close()



if __name__ == '__main__':
    langs = sys.argv[1:]
    for lang in langs:
        do_lang(lang)
