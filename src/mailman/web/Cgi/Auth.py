# Copyright (C) 1998-2009 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Common routines for logging in and logging out of the list administrator
and list moderator interface.
"""

from Mailman import Utils
from Mailman.htmlformat import FontAttr
from Mailman.i18n import _



class NotLoggedInError(Exception):
    """Exception raised when no matching admin cookie was found."""
    def __init__(self, message):
        Exception.__init__(self, message)
        self.message = message



def loginpage(mlist, scriptname, msg='', frontpage=False):
    url = mlist.GetScriptURL(scriptname)
    if frontpage:
        actionurl = url
    else:
        request = Utils.GetRequestURI(url).lstrip('/')
        up = '../' * request.count('/')
        actionurl = up + request
    if msg:
        msg = FontAttr(msg, color='#ff0000', size='+1').Format()
    if scriptname == 'admindb':
        who = _('Moderator')
    else:
        who = _('Administrator')
    # Language stuff
    charset = Utils.GetCharSet(mlist.preferred_language)
    print 'Content-type: text/html; charset=' + charset + '\n\n'
    print Utils.maketext(
        'admlogin.html',
        {'listname': mlist.real_name,
         'path'    : actionurl,
         'message' : msg,
         'who'     : who,
         }, mlist=mlist).encode(charset)
    print mlist.GetMailmanFooter().encode(charset)
