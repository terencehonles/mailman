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

"""Common routines for logging in and logging out of the admin interface.
"""

from Mailman import Utils
from Mailman import Errors
from Mailman.htmlformat import FontAttr
from Mailman.i18n import _



class NotLoggedInError(Exception):
    """Exception raised when no matching admin cookie was found."""
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message



def loginpage(mlist, scriptname, msg='', frontpage=None):
    url = mlist.GetScriptURL(scriptname)
    if frontpage:
        actionurl = url
    else:
        actionurl = Utils.GetRequestURI(url)
    if msg:
        msg = FontAttr(msg, color='#ff0000', size='+1').Format()
    # Language stuff
    charset = Utils.GetCharSet(mlist.preferred_language)
    print 'Content-type: text/html; charset=' + charset + '\n\n'
    print Utils.maketext(
        # Should really be admlogin.html :/
        'admlogin.txt',
        {'listname': mlist.real_name,
         'path'    : actionurl,
         'message' : msg,
         }, mlist=mlist)

    

def authenticate(mlist, cgidata):
    # Returns 1 if the user is properly authenticated, otherwise it does
    # everything necessary to put up a login screen and returns 0.
    isauthed = 0
    adminpw = None
    msg = ''
    #
    # If we get a password change request, we first authenticate by cookie
    # here, and issue a new cookie later on iff the password change worked
    # out.  The idea is to set only one cookie when the admin password
    # changes.  The new cookie is necessary, because the checksum part of the
    # cookie is based on (among other things) the list's admin password.
    if cgidata.has_key('adminpw') and \
           cgidata['adminpw'].value and \
           not cgidata.has_key('newpw'):
        # then
        adminpw = cgidata['adminpw'].value
    # Attempt to authenticate
    try:
        isauthed = mlist.WebAuthenticate(password=adminpw, cookie='admin')
    except Errors.MMExpiredCookieError:
        msg = _('Stale cookie found')
    except Errors.MMInvalidCookieError:
        msg = _('Error decoding authorization cookie')
    except (Errors.MMBadPasswordError, Errors.MMAuthenticationError):
        msg = _('Authentication failed')
    #
    # Returns successfully if logged in
    if not isauthed:
        raise NotLoggedInError(msg)
