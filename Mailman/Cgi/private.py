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

"""Provide a password-interface wrapper around private archives.

Currently this is organized to obtain passwords for Mailman mailing list
subscribers.
"""

import sys, os, string, cgi
from Mailman import Utils, MailList, Errors
from Mailman.htmlformat import *
from Mailman.Logging.Utils import LogStdErr
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog

LogStdErr("error", "private")


PAGE = '''
<html>
<head>
  <title>%(listname)s Private Archives Authentication</title>
</head>
<body bgcolor="#ffffff">
<FORM METHOD=POST ACTION="%(basepath)s/">
  <TABLE WIDTH="100%%" BORDER="0" CELLSPACING="4" CELLPADDING="5">
    <TR>
      <TD COLSPAN="2" WIDTH="100%%" BGCOLOR="#99CCFF" ALIGN="CENTER">
	<B><FONT COLOR="#000000" SIZE="+1">%(listname)s Private Archives
	    Authentication</FONT></B>
      </TD>
    </TR>
    <tr>
      <td COLSPAN="2"> <P>%(message)s </td>
    <tr>
    </tr>
      <TD> <div ALIGN="Right">Address:  </div></TD>
      <TD> <INPUT TYPE=TEXT NAME=username SIZE=30> </TD>
    <tr>
    </tr>
      <TD> <div ALIGN="Right"> Password: </div> </TD>
      <TD> <INPUT TYPE=password NAME=password SIZE=30></TD>
    <tr>
    </tr>
      <td></td>
      <td> <INPUT TYPE=SUBMIT VALUE="Let me in...">
      </td>
    </tr>
  </TABLE>
      <p><strong><em>Important:</em></strong> From this point on, you
      must have cookies enabled in your browser, otherwise you will not
      be able to read the private archives.

      <p>Session cookies are used in the private archives so that you
      don\'t need to re-authenticate for every article your read.  This
      cookie will expire automatically when you exit your browser.
</FORM>
'''

	
login_attempted = 0
_list = None

def true_path(path):
    "Ensure that the path is safe by removing .."
    path = string.replace(path, "../", "")
    path = string.replace(path, "./", "")
    return path[1:]


def content_type(path):
    if path[-3:] == '.gz':
        path = path[:-3]
    if path[-4:] == '.txt':
        return 'text/plain'
    return 'text/html'


def main():
    doc = Document()
    parts = Utils.GetPathPieces()
    if not parts:
        doc.SetTitle("Private Archive Error")
        doc.AddItem(Header(3, "You must specify a list."))
        print doc.Format(bgcolor="#FFFFFF")
        sys.exit(0)

    path = os.environ.get('PATH_INFO')
    true_filename = os.path.join(
        mm_cfg.PRIVATE_ARCHIVE_FILE_DIR,
        true_path(path))

    listname = string.lower(parts[0])
    mboxfile = ''
    if len(parts) > 1:
        mboxfile = parts[1]

    # See if it's the list's mbox file is being requested
    if listname[-5:] == '.mbox' and mboxfile[-5:] == '.mbox' and \
           listname[:-5] == mboxfile[:-5]:
        listname = listname[:-5]
    else:
        mboxfile = ''

    # If it's a directory, we have to append index.html in this script.  We
    # must also check for a gzipped file, because the text archives are
    # usually stored in compressed form.
    if os.path.isdir(true_filename):
        true_filename = true_filename + '/index.html'
    if not os.path.exists(true_filename) and \
       os.path.exists(true_filename + '.gz'):
        # then
        true_filename = true_filename + '.gz'

    try:
        mlist = MailList.MailList(listname, lock=0)
        mlist.IsListInitialized()
    except Errors.MMListError, e:
        msg = 'No such list <em>%s</em>' % listname
        doc.SetTitle("Private Archive Error - %s" % msg)
        doc.AddItem(Header(2, msg))
        print doc.Format(bgcolor="#FFFFFF")
        syslog('error', 'No such list "%s": %s\n' % (listname, e))
        sys.exit(0)

    form = cgi.FieldStorage()
    user = password = None
    if form.has_key('username'):
	user = form['username']
	if type(user) == type([]): user = user[0]
	user = user.value
    if form.has_key('password'): 
	password = form['password']
	if type(password) == type([]): password = password[0]
	password = password.value

    is_auth = 0
    message = ("Please enter your %s subscription email address "
               "and password." % mlist.real_name)
    try:
        is_auth = mlist.WebAuthenticate(user=user,
                                          password=password,
                                          cookie='archive')
    except (Errors.MMBadUserError, Errors.MMBadPasswordError,
            Errors.MMNotAMemberError): 
        message = ('Your email address or password were incorrect. '
                   'Please try again.')
    except Errors.MMExpiredCookieError:
        message = 'Your cookie has gone stale, ' \
                  'enter password to get a new one.',
    except Errors.MMInvalidCookieError:
        message = 'Error decoding authorization cookie.'
    except Errors.MMAuthenticationError:
        message = 'Authentication error.'
    
    if not is_auth:
        # Output the password form
        print 'Content-type: text/html\n\n'
        page = PAGE
        while path and path[0] == '/': path=path[1:]  # Remove leading /'s
        basepath = os.path.split(mlist.GetBaseArchiveURL())[0]
        listname = mlist.real_name
        print page % vars()
        sys.exit(0)

    # Authorization confirmed... output the desired file
    try:
        ctype = content_type(path)
        if mboxfile:
            f = open(os.path.join(mlist.archive_directory + '.mbox',
                                  mlist.internal_name() + '.mbox'))
            ctype = 'text/plain'
        elif true_filename[-3:] == '.gz':
            import gzip
            f = gzip.open(true_filename, 'r')
        else:
            f = open(true_filename, 'r')
    except IOError:
        print 'Content-type: text/html\n'

        print "<H3>Archive File Not Found</H3>"
        print "No file", path, '(%s)' % true_filename
    else:
        print 'Content-type: %s\n' % ctype
        sys.stdout.write(f.read())
        f.close()
