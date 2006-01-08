#! /usr/bin/env python
# Move language templates to po file.
# This should be one time task of source code transition.
# Code stolen from pygettext.py
# by Tokio Kikuchi <tkikuchi@is.kochi-u.ac.jp>

"""templ2po.py -- convert mailman language to po file.

Usage: templ2po.py language ...

Options:

    -h, --help

Language is in IANA format.
"""

import sys
import os
import getopt

try:
    import paths
    from Mailman.i18n import _
except ImportError:
    def _(s): return s

EMPTYSTRING = ''


def usage(code, msg=''):
    if code:
        fd = sys.stderr
    else:
        fd = sys.stdout
    print >> fd, _(__doc__) % globals()
    if msg:
        print >> fd, msg
    sys.exit(code)



escapes = []

def make_escapes(pass_iso8859):
    global escapes
    if pass_iso8859:
        # Allow iso-8859 characters to pass through so that e.g. 'msgid
        # "H[o-umlaut]he"' would result not result in 'msgid "H\366he"'.
        # Otherwise we escape any character outside the 32..126 range.
        mod = 128
    else:
        mod = 256
    for i in range(256):
        if 32 <= (i % mod) <= 126:
            escapes.append(chr(i))
        else:
            escapes.append("\\%03o" % i)
    escapes[ord('\\')] = '\\\\'
    escapes[ord('\t')] = '\\t'
    escapes[ord('\r')] = '\\r'
    escapes[ord('\n')] = '\\n'
    escapes[ord('\"')] = '\\"'


def escape(s, eightbit):
    global escapes
    s = list(s)
    for i in range(len(s)):
        if eightbit and ord(s[i]) > 127:
            pass
        else:
            s[i] = escapes[ord(s[i])]
    return EMPTYSTRING.join(s)


def normalize(s, eightbit):
    # This converts the various Python string types into a format that is
    # appropriate for .po files, namely much closer to C style.
    lines = s.splitlines()
    if len(lines) == 1:
        s = '"' + escape(s, eightbit) + '"'
    else:
        if not lines[-1]:
            del lines[-1]
            lines[-1] = lines[-1] + '\n'
        for i in range(len(lines)):
            lines[i] = escape(lines[i], eightbit)
        lineterm = '\\n"\n"'
        s = '""\n"' + lineterm.join(lines) + '"'
    return s



def main():
    try:
        opts, args = getopt.getopt(
            sys.argv[1:],
            'h',
            ['help',]
             )
    except getopt.error, msg:
        usage(1, msg)

    # parse options
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            usage(0)

    # calculate escapes
    make_escapes(0)

    for lang in args:
        filenames = os.listdir('templates/%s' % lang)
        filenames.remove('CVS')
        outfile = file('messages/%s/LC_MESSAGES/mailman.po' % lang, 'a')
        for filename in filenames:
            try:
                s = file('templates/en/%s' % filename).read()
                print >> outfile, '#: templates/en/%s:1' % filename
                print >> outfile, '#, template'
                print >> outfile, 'msgid', normalize(s, 0)
                s = file('templates/%s/%s' % (lang, filename)).read()
                print >> outfile, 'msgstr', normalize(s, 1)
                print >> outfile
            except IOError:
                continue


if __name__ == '__main__':
    main()
