#! @PYTHON@
# Quick hack by Tokio Kikuchi <tkikuchi@is.kochi-u.ac.jp>

""" po2templ.py

    extract templates from language po file.

Usage: po2templ.py languages

"""

import sys

def do_lang(lang):
    in_template = 0
    in_msg = 0
    msgstr = ''
    for i in file('messages/%s/LC_MESSAGES/mailman.po' % lang):
        if i.startswith('#: templates'):
            in_template = 1
            in_msg = 0
            filename = i[16:-3]
            outfile = file('templates/%s/%s' % (lang, filename), 'w')
            continue
        if in_template and i.startswith('#,'):
            continue
        if in_template and i.startswith('msgstr'):
            i = i[7:]
            in_msg = 1
        if in_msg:
            if len(i.strip()) == 0:
                in_template = 0
                in_msg = 0
                print >> outfile, msgstr
                outfile.close()
                msgstr = ''
                continue
            msgstr += eval(i)

if __name__ == '__main__':
    langs = sys.argv[1:]
    for lang in langs:
        do_lang(lang)
