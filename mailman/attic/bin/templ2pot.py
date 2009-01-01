#! @PYTHON@
# Code stolen from pygettext.py
# by Tokio Kikuchi <tkikuchi@is.kochi-u.ac.jp>

"""templ2pot.py -- convert mailman template (en) to pot format.

Usage: templ2pot.py inputfile ...

Options:

    -h, --help

Inputfiles are english templates.  Outputs are written to stdout.
"""

import sys
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


def escape(s):
    global escapes
    s = list(s)
    for i in range(len(s)):
        s[i] = escapes[ord(s[i])]
    return EMPTYSTRING.join(s)


def normalize(s):
    # This converts the various Python string types into a format that is
    # appropriate for .po files, namely much closer to C style.
    lines = s.splitlines()
    if len(lines) == 1:
        s = '"' + escape(s) + '"'
    else:
        if not lines[-1]:
            del lines[-1]
            lines[-1] = lines[-1] + '\n'
        for i in range(len(lines)):
            lines[i] = escape(lines[i])
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

    for filename in args:
        print '#: %s:1' % filename
        s = file(filename).read()
        print '#, template'
        print 'msgid', normalize(s)
        print 'msgstr ""\n'



if __name__ == '__main__':
    main()
