#! /usr/bin/env python -u
#
# Copyright (C) 1998 by the Free Software Foundation, Inc.
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

"""Provide a password-interface wrapper around a hierarchy of web pages.

Currently this is organized to obtain passwords for mailman maillist
subscribers.

 - Set the ROOT variable to point to the root of your archives private
   hierarchy.  The script will look there for the private archive files.
 - Put the ../misc/Cookie.py script in ../../cgi-bin (where the wrapper
   executables are).
"""

import sys, os, string
from Mailman import MailList, Errors
from Mailman import Cookie
from Mailman.Logging.Utils import LogStdErr
import Mailman.mm_cfg

LogStdErr("error", "private")



ROOT = os.path.join(Mailman.mm_cfg.PREFIX, "public_html/archives")
SECRET = "secret"  # XXX used for hashing

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
      <td> <INPUT TYPE=SUBMIT>
      </td>
    </tr>
  </TABLE>
</FORM>
'''

	
login_attempted = 0
_list = None

def getListName(path):
    return string.split(path, os.sep)[1]


def GetListobj(list_name):
    """Return an unlocked instance of the named maillist, if found."""
    global _list
    if _list:
	return _list
    try:
        _list = MailList.MailList(list_name, lock=0)
    except Errors.MMUnknownListError:
	_list = None
	return None
    return _list

def isAuthenticated(list_name):
    if os.environ.has_key('HTTP_COOKIE'):
	c = Cookie.Cookie( os.environ['HTTP_COOKIE'] )
	if c.has_key(list_name):
            if c[list_name].value == `hash(list_name)`:
                return 1
    # No corresponding cookie.  OK, then check for username, password
    # CGI variables 
    import cgi
    v = cgi.FieldStorage()
    username = password = None
    if v.has_key('username'): 
	username = v['username']
	if type(username) == type([]): username = username[0]
	username = username.value
    if v.has_key('password'): 
	password = v['password']
	if type(password) == type([]): password = password[0]
	password = password.value
	
    if username is None or password is None: return 0

    # Record that this is a login attempt, so if it fails the form can
    # be displayed with an appropriate message.
    global login_attempted
    login_attempted=1
    listobj = GetListobj(list_name)
    if not listobj:
        print '\n<P>A list named,', repr(list_name), "was not found."
        return 0
    try:
	listobj.ConfirmUserPassword( username, password)
    except (Errors.MMBadUserError, Errors.MMBadPasswordError): 
	return 0

    token = `hash(list_name)`
    c = Cookie.Cookie()
    c[list_name] = token
    print c				# Output the cookie
    return 1


def true_path(path):
    "Ensure that the path is safe by removing .."
    path = string.replace(path, "../", "")
    path = string.replace(path, "./", "")
    return path[1:]


def main():
    path = os.environ.get('PATH_INFO', "/index.html")
    true_filename = os.path.join(ROOT, true_path(path) )
    list_name = getListName(path)
    if os.path.isdir(true_filename):
        true_filename = true_filename + '/index.html'

    if not isAuthenticated(list_name):
        # Output the password form
        print 'Content-type: text/html\n'
        page = PAGE
            
        listobj = GetListobj(list_name)
        if login_attempted:
            message = ("Your email address or password were incorrect."
                       " Please try again.")
        else:
            message = ("Please enter your %s subscription email address"
                       " and password." % listobj.real_name)
        while path and path[0] == '/': path=path[1:]  # Remove leading /'s
        basepath = os.path.split(listobj.GetBaseArchiveURL())[0]
        listname = listobj.real_name
        print '\n\n', page % vars()
        sys.exit(0)
    print 'Content-type: text/html\n'
    
    print '\n\n'
    # Authorization confirmed... output the desired file
    try:
        f = open(true_filename, 'r')
    except IOError:
        print "<H3>Archive File Not Found</H3>"
        print "No file", path
    else:
        while (1):
            data = f.read(16384)
            if data == "": break
            sys.stdout.write(data)
        f.close()


