# Copyright (C) 1998,1999,2000,2001 by the Free Software Foundation, Inc.
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

import sys
import os
import cgi

from Mailman import Utils, MailList, Errors
from Mailman.htmlformat import *
from Mailman.Logging.Utils import LogStdErr
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog
from Mailman.i18n import _

LogStdErr("error", "private")

login_attempted = 0
_list = None

def true_path(path):
    "Ensure that the path is safe by removing .."
    path = path.replace('../', '')
    path = path.replace('./', '')
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
        doc.SetTitle(_("Private Archive Error"))
        doc.AddItem(Header(3, _("You must specify a list.")))
        print doc.Format()
        sys.exit(0)

    path = os.environ.get('PATH_INFO')
    true_filename = os.path.join(
        mm_cfg.PRIVATE_ARCHIVE_FILE_DIR,
        true_path(path))

    listname = parts[0].lower()
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
        msg = _('No such list <em>%(listname)s</em>')
        doc.SetTitle(_("Private Archive Error - %(msg)s"))
        doc.AddItem(Header(2, msg))
        print doc.Format()
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
    realname = mlist.real_name
    message = (_("Please enter your %(realname)s subscription email address "
               "and password."))
    try:
        is_auth = mlist.WebAuthenticate(user=user,
                                          password=password,
                                          cookie='archive')
    except (Errors.MMBadUserError, Errors.MMBadPasswordError,
            Errors.MMNotAMemberError): 
        message = (_('Your email address or password were incorrect. '
                   'Please try again.'))
    except Errors.MMExpiredCookieError:
        message = _('Your cookie has gone stale, ' \
                  'enter password to get a new one.'),
    except Errors.MMInvalidCookieError:
        message = _('Error decoding authorization cookie.')
    except Errors.MMAuthenticationError:
        message = _('Authentication error.')
    
    if not is_auth:
        # Output the password form
        charset = Utils.GetCharSet(mlist.preferred_language)
        print 'Content-type: text/html; charset=' + charset + '\n\n'
        while path and path[0] == '/':
            path=path[1:]  # Remove leading /'s
        print Utils.maketext(
            'private.html',
            {'action'  : mlist.GetScriptURL('private', absolute=1),
             'realname': mlist.real_name,
             'message' : message,
             }, mlist=mlist)
        return

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
        print 'Content-type: text/html; charset=' + Utils.GetCharSet() + '\n\n'

        print "<H3>" + _("Archive File Not Found") + "</H3>"
        print _("No file"), path, '(%s)' % true_filename
    else:
        print 'Content-type: %s\n' % ctype
        sys.stdout.write(f.read())
        f.close()
