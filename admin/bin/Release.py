#! /usr/bin/env python

"""Manage releases of Mailman.

Usage: %(program)s [-b newvers] [-t|-T tagname] [-p] [-d] [-h]

Where:

    --tag tagname
    -t tagname
        Tag all release files with tagname.

    --TAG tagname
    -T tagname
        Like --tag, but relocates any existing tag.  See `cvs tag -F'.  Only
        one of --tag or --TAG can be given on the command line.

    --package
    -p
        create the distribution package

    --bump newvers
    -b newvers
        Bump the revision number in key files to the specified newvers.  This
        is done by textual substitution.

    --help
    -h
        Print this help message.

"""

import sys
import os
import string
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

CVSREPOS = ':pserver:mailmancvs@cvs.python.org:/projects/cvsroot'

def cvsdo(cvscmd, remrepos=0):
    repos = ''
    if remrepos:
        repos = '-d %s' % CVSREPOS
    os.system('cvs %s %s' % (repos, cvscmd))

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
    os.chdir(tmpdir)
    # must have already logged in
    cvsdo('export -k kv -r %s -d %s mailman' % (tagname, releasedir()), 1)


def make_pkg(tagname):
    tarball = releasedir() + '.tgz'
    os.system('tar cvf - %s | gzip -c > %s' % (releasedir(), tarball))

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
    print 'configure.in...',
    fp_in = open('configure.in')
    fp_out = open('configure.in.new', 'w')
    matched = 0
    while 1:
        line = fp_in.readline()
        if not line:
            break
        if not matched and line[:8] == 'VERSION=':
            fp_out.write('VERSION=' + newvers + '\n')
            matched = 1
        else:
            fp_out.write(line)
    fp_in.close()
    fp_out.close()
    os.rename('configure.in.new', 'configure.in')
    os.system('autoreconf')
    # update the TODO file
    print 'TODO...'
    os.system('admin/bin/mm2do')


def main():
    try:
	opts, args = getopt.getopt(
	    sys.argv[1:],
	    'b:t:T:ph',
	    ['bump=', 'tag=', 'TAG=', 'package', 'help'])
    except getopt.error, msg:
	print msg
	usage(1)

    # required minor rev number
    if args:
	usage(1)

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
            tagname = arg
	elif opt in ('-T', '--TAG'):
	    tag = 1
            tagname = arg
	    retag = 1
	elif opt in ('-p', '--package'):
	    package = 1
        elif opt in ('-b', '--bump'):
            bump = 1
            newvers = arg

    # very important!!!
    omask = os.umask(0)
    try:
        if tag:
            tag_release(tagname, retag)

        if package:
            pkg_release(revnum)

        if bump:
            do_bump(newvers)
    finally:
        os.umask(omask)

if __name__ == '__main__':
    main()
