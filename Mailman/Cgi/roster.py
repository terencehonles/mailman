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
import os, string
import cgi

from Mailman import Utils
from Mailman import MailList
from Mailman import htmlformat
from Mailman import Errors
from Mailman import mm_cfg
from Mailman.Logging.Syslog import syslog
from Mailman.i18n import _



def main():
    doc = htmlformat.HeadlessDocument()

    parts = Utils.GetPathPieces()
    if not parts:
        error_page(_('Invalid options to CGI script'))
        return

    listname = string.lower(parts[0])
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        error_page(_('No such list <em>%(listname)s</em>'))
        syslog('error', 'roster: no such list "%s": %s' % (listname, e))
        return

    form = cgi.FieldStorage()

    # messages in form should go in selected language (if any...)
    if form.has_key('language'):
       os.environ['LANG'] = lang = form['language'].value
    else:
       os.environ['LANG'] = lang = mlist.preferred_language

    bad = ""
    # These nested conditionals constituted a cascading authentication
    # check, yielding a 
    # jcrey:
    # Already in roster page, an user may desire to see roster page 
    # in a different language in a list with privacy access

    try:
       FromURL = os.environ['HTTP_REFERER']
    except KeyError:
       FromURL = ''
    
    if not mlist.private_roster or \
           mlist.GetScriptURL('roster', absolute=1) == FromURL:
        # No privacy.
        bad = ""
    else:
        realname = mlist.real_name
        auth_req = _("%(realname)s subscriber list requires authentication.")
        if not form.has_key("roster-pw"):
            bad = auth_req
        else:
            pw = form['roster-pw'].value
            # Just the admin password is sufficient - check it early.
            if not mlist.ValidAdminPassword(pw):
                if not form.has_key('roster-email'):
                    # No admin password and no user id, nogo.
                    bad = auth_req
                else:
                    id = form['roster-email'].value
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
        doc = error_page_doc(bad)
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format()
        sys.exit(0)

    replacements = mlist.GetAllReplacements(lang)
    replacements['<mm-displang-box>'] = mlist.FormatButton(
        'displang-button',
        text = _('See this page in'))
    replacements['<mm-lang-form-start>'] = mlist.FormatFormStart('roster')
    doc.AddItem(mlist.ParseTags('roster.html', replacements, lang))
    print doc.Format()



def error_page(errmsg, *args):
    print apply(error_page_doc, (errmsg,) + args).Format()


def error_page_doc(errmsg, *args):
    """Produce a simple error-message page on stdout and exit.

    Optional arg justreturn means just return the doc, don't print it."""
    doc = htmlformat.Document()
    doc.SetTitle(_("Error"))
    doc.AddItem(htmlformat.Header(2, _("Error")))
    doc.AddItem(htmlformat.Bold(errmsg % args))
    return doc







