# Copyright (C) 1998-2008 by the Free Software Foundation, Inc.
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

"""Produce subscriber roster, using listinfo form data, roster.html template.

Takes listname in PATH_INFO.
"""


# We don't need to lock in this script, because we're never going to change
# data.

import os
import cgi
import sys
import urllib
import logging

from Mailman import Errors
from Mailman import MailList
from Mailman import Utils
from Mailman import i18n
from Mailman.configuration import config
from Mailman.htmlformat import *

# Set up i18n
_ = i18n._
i18n.set_language(config.DEFAULT_SERVER_LANGUAGE)

log = logging.getLogger('mailman.error')



def main():
    parts = Utils.GetPathPieces()
    if not parts:
        error_page(_('Invalid options to CGI script'))
        return

    listname = parts[0].lower()
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        # Avoid cross-site scripting attacks
        safelistname = Utils.websafe(listname)
        error_page(_('No such list <em>%(safelistname)s</em>'))
        log.error('roster: no such list "%s": %s', listname, e)
        return

    cgidata = cgi.FieldStorage()

    # messages in form should go in selected language (if any...)
    lang = cgidata.getvalue('language')
    if lang not in config.languages.enabled_codes:
        lang = mlist.preferred_language
    i18n.set_language(lang)

    # Perform authentication for protected rosters.  If the roster isn't
    # protected, then anybody can see the pages.  If members-only or
    # "admin"-only, then we try to cookie authenticate the user, and failing
    # that, we check roster-email and roster-pw fields for a valid password.
    # (also allowed: the list moderator, the list admin, and the site admin).
    if mlist.private_roster == 0:
        # No privacy
        ok = 1
    elif mlist.private_roster == 1:
        # Members only
        addr = cgidata.getvalue('roster-email', '')
        password = cgidata.getvalue('roster-pw', '')
        ok = mlist.WebAuthenticate((config.AuthUser,
                                    config.AuthListModerator,
                                    config.AuthListAdmin,
                                    config.AuthSiteAdmin),
                                   password, addr)
    else:
        # Admin only, so we can ignore the address field
        password = cgidata.getvalue('roster-pw', '')
        ok = mlist.WebAuthenticate((config.AuthListModerator,
                                    config.AuthListAdmin,
                                    config.AuthSiteAdmin),
                                   password)
    if not ok:
        realname = mlist.real_name
        doc = Document()
        doc.set_language(lang)
        error_page_doc(doc, _('%(realname)s roster authentication failed.'))
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
    doc.set_language(config.DEFAULT_SERVER_LANGUAGE)
    error_page_doc(doc, errmsg)
    print doc.Format()


def error_page_doc(doc, errmsg, *args):
    # Produce a simple error-message page on stdout and exit.
    doc.SetTitle(_("Error"))
    doc.AddItem(Header(2, _("Error")))
    doc.AddItem(Bold(errmsg % args))
