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

"""Produce subscriber roster, using listinfo form data, roster.html template.

Takes listname in PATH_INFO.
"""


# We don't need to lock in this script, because we're never going to change
# data. 

import sys
import os
import cgi
import urllib

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman import i18n
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog

# Set up i18n
_ = i18n._
i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)



def main():
    parts = Utils.GetPathPieces()
    if not parts:
        error_page(_('Invalid options to CGI script'))
        return

    listname = parts[0].lower()
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        error_page(_('No such list <em>%(listname)s</em>'))
        syslog('error', 'roster: no such list "%s": %s' % (listname, e))
        return

    cgidata = cgi.FieldStorage()

    # messages in form should go in selected language (if any...)
    if cgidata.has_key('language'):
        lang = cgidata['language'].value
    else:
        lang = mlist.preferred_language

    i18n.set_language(lang)
    bad = ''
    # These nested conditionals constituted a cascading authentication
    # check, yielding a 
    # jcrey:
    # Already in roster page, an user may desire to see roster page 
    # in a different language in a list with privacy access

    fromurl = os.environ.get('HTTP_REFERER', '')
    
    if not mlist.private_roster or \
           mlist.GetScriptURL('roster', absolute=1) == fromurl:
        # No privacy.
        bad = ''
    else:
        realname = mlist.real_name
        auth_req = _("%(realname)s subscriber list requires authentication.")
        if not cgidata.has_key("roster-pw"):
            bad = auth_req
        else:
            pw = cgidata['roster-pw'].value
            # Just the admin password is sufficient - check it early.
            if not mlist.ValidAdminPassword(pw):
                if not cgidata.has_key('roster-email'):
                    # No admin password and no user id, nogo.
                    bad = auth_req
                else:
                    id = cgidata['roster-email'].value
                    if mlist.private_roster == 1:
                        # Private list - members visible.
                        try:
                            mlist.ConfirmUserPassword(id, pw)
                        except (Errors.MMBadUserError, 
                                Errors.MMBadPasswordError,
                                Errors.MMNotAMemberError):
                            bad = _(
                              "%(realname)s subscriber authentication failed.")
                    else:
                        # Anonymous list - admin-only visible
                        # - and we already tried admin password, above.
                        bad = _("%(realname)s admin authentication failed.")
    if bad:
        doc = Document()
        doc.set_language(lang)
        error_page_doc(doc, bad)
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format()
        return

    # The document and its language
    doc = HeadlessDocument()
    doc.set_language(lang)

    replacements = mlist.GetAllReplacements(lang)
    replacements['<mm-displang-box>'] = mlist.FormatButton(
        'displang-button',
        text = _('View this page in'))
    replacements['<mm-lang-form-start>'] = mlist.FormatFormStart('roster')
    doc.AddItem(mlist.ParseTags('roster.html', replacements, lang))
    print doc.Format()



def error_page(errmsg):
    doc = Document()
    doc.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)
    error_page_doc(doc, errmsg)
    print doc.Format()


def error_page_doc(doc, errmsg, *args):
    # Produce a simple error-message page on stdout and exit.
    doc.SetTitle(_("Error"))
    doc.AddItem(Header(2, _("Error")))
    doc.AddItem(Bold(errmsg % args))
