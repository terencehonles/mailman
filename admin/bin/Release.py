#! /usr/bin/env python
#
# Copyright (C) 1998,1999,2000 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""Manage releases of Mailman.

Usage: %(program)s [options] tagname

Where `options' are:

    --tag
    -t
        Tag all release files with tagname.

    --TAG
    -T
        Like --tag, but relocates any existing tag.  See `cvs tag -F'.  Only
        one of --tag or --TAG can be given on the command line.

    --package
    -p
        create the distribution package

    --bump
    -b
        Bump the revision number in key files to tagname.  This is done by
        textual substitution.

    --help
    -h
        Print this help message.

    tagname is used in the various commands above.  It should essentially be
    the version number for the release, and is required.

"""

import sys
import os
import string
import re
import time
import tempfile
import getopt

program = sys.argv[0]

def usage(status, msg=''):
    print __doc__ % globals()
    if msg:
        print msg
    sys.exit(status)


_releasedir = None
def releasedir(tagname=None):
    global _releasedir
    if not _releasedir:
        tmpdir = tempfile.gettempdir()
        _releasedir = os.path.join(tmpdir, 'mailman-' + tagname)
    return _releasedir
        


# CVS related commands

def cvsdo(cvscmd):
    os.system('cvs %s' % cvscmd)

def tag_release(tagname, retag):
    # watch out for dots in the name
    table = string.maketrans('.', '_')
    # To be done from writeable repository
    relname = '"Release_' + string.translate(tagname, table) + '"'
    print 'Tagging release with', relname, '...'
    option = ''
    if retag:
	option = '-F'
    cvsdo('tag %s %s' % (option, relname))

def checkout(tagname):
    print 'checking out...',
    # watch out for dots in the name
    table = string.maketrans('.', '_')
    # To be done from writeable repository
    relname = '"Release_' + string.translate(tagname, table) + '"'
    cvsdo('export -k kv -r %s -d %s mailman' % (relname, releasedir()))
    os.rename('%s/doc' % releasedir(), 'mailman-doc')



def make_pkg(tagname):
    print 'Creating release dir', releasedir(tagname), '...'
    # this can't be done from a working directory
    curdir = os.getcwd()
    try:
        os.chdir(tempfile.gettempdir())
        checkout(tagname)
        print 'making tarball...'
        tarball = releasedir() + '.tgz'
        os.system('tar cvf - %s | gzip -c > %s' %
                  ('mailman-' + tagname, tarball))
        os.system('tar cvf - mailman-doc | gzip -c > mailman-doc.gz')
    finally:
        os.chdir(curdir)


def do_bump(newvers):
    print 'doing bump...',
    # hack the index.html file
    print 'index.html...',
    fp = open('admin/www/index.html', 'r+')
    text = fp.read()
    parts = string.split(text, '<!-VERSION--->')
    parts[1] = newvers
    text = string.join(parts, '<!-VERSION--->')
    parts = string.split(text, '<!-DATE--->')
    timestr = time.ctime(time.time())
    parts[1] = timestr[4:11] + timestr[-4:]
    text = string.join(parts, '<!-DATE--->')
    fp.seek(0)
    fp.write(text)
    fp.close()
    # hack the configure.in file
    print 'Version.py...',
    fp_in = open('Mailman/Version.py')
    fp_out = open('Mailman/Version.py.new', 'w')
    matched = 0
    cre = re.compile(r'^VERSION(?P<ws>[ \t]*)=')
    while 1:
        line = fp_in.readline()
        if not line:
            if not matched:
                print 'Error! VERSION line not found'
            break
        mo = cre.search(line)
        if matched or not mo:
            fp_out.write(line)
        else:
            fp_out.write('VERSION%s= "%s"\n' % (mo.group('ws'), newvers))
            matched = 1
    fp_in.close()
    fp_out.close()
    os.rename('Mailman/Version.py.new', 'Mailman/Version.py')
    # update the TODO file
    print 'TODO...'
    os.system('admin/bin/mm2do')


def main():
    try:
	opts, args = getopt.getopt(
	    sys.argv[1:],
	    'btTph',
	    ['bump', 'tag', 'TAG', 'package', 'help'])
    except getopt.error, msg:
	usage(1, msg)

    # required minor rev number
    if len(args) <> 1:
	usage(1, 'tagname argument is required')

    tagname = args[0]

    # default options
    tag = 0
    retag = 0
    package = 0
    bump = 0

    for opt, arg in opts:
	if opt in ('-h', '--help'):
	    usage(0)
	elif opt in ('-t', '--tag'):
	    tag = 1
	elif opt in ('-T', '--TAG'):
	    tag = 1
	    retag = 1
	elif opt in ('-p', '--package'):
	    package = 1
        elif opt in ('-b', '--bump'):
            bump = 1

    # very important!!!
    omask = os.umask(0)
    try:
        if tag:
            tag_release(tagname, retag)

        if package:
            make_pkg(tagname)

        if bump:
            do_bump(tagname)
    finally:
        os.umask(omask)

if __name__ == '__main__':
    main()
