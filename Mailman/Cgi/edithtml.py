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

"""Script which implements admin editing of the list's html templates."""

import os
import cgi
import gettext

from Mailman import Utils
from Mailman import MailList
from Mailman.htmlformat import *
from Mailman.HTMLFormatter import HTMLFormatter
from Mailman import Errors
from Mailman.Cgi import Auth
from Mailman.Logging.Syslog import syslog
from Mailman import i18n



def main():
    # Trick out pygettext since we want to mark template_data as translatable,
    # but we don't want to actually translate it here.
    def _(s):
        return s

    template_data = (
        ('listinfo.html',    _('General list information page')),
        ('subscribe.html',   _('Subscribe results page')),
        ('options.html',     _('User specific options page')),
        ('handle_opts.html', _('Changing user options results page')),
        )

    doc = Document()

    # Set up the system default language
    _ = i18n._
    i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)
    doc.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)

    parts = Utils.GetPathPieces()
    if not parts:
        doc.AddItem(Header(2, _("List name is required.")))
        print doc.Format(bgcolor='#ffffff')
        return

    listname = parts[0].lower()
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        doc.AddItem(Header(2, _('No such list <em>%(listname)s</em>')))
        print doc.Format(bgcolor='#ffffff')
        syslog('error', _('No such list "%(listname)s": %(e)s\n'))
        return

    # Now that we have a valid list, set the language to its default
    i18n.set_language(mlist.preferred_language)
    doc.set_language(mlist.preferred_language)

    # Must be authenticated to get any farther
    cgidata = cgi.FieldStorage()
    try:
        Auth.authenticate(mlist, cgidata)
    except Auth.NotLoggedInError, e:
        Auth.loginpage(mlist, 'edithtml', e.message)
        return

    # get the list._template_dir attribute
    HTMLFormatter.InitVars(mlist)

    realname = mlist.real_name
    if len(parts) > 1:
        template_name = parts[1]
        for (template, info) in template_data:
            if template == template_name:
                template_info = _(info)
                doc.SetTitle(_(
                    '%(realname)s -- Edit html for %(template_info)s'))
                break
        else:
            doc.SetTitle(_('Edit HTML : Error'))
            doc.AddItem(Header(2, _("%(template_name)s: Invalid template")))
            doc.AddItem(mlist.GetMailmanFooter())
            print doc.Format(bgcolor='#ffffff')
            return
    else:
        doc.SetTitle(_('%(realname)s -- HTML Page Editing'))
        doc.AddItem(Header(1, _('%(realname)s -- HTML Page Editing')))
        doc.AddItem(Header(2, _('Select page to edit:')))
        template_list = UnorderedList()
        for (template, info) in template_data:
            l = Link(mlist.GetScriptURL('edithtml') + '/' + template, _(info))
            template_list.AddItem(l)
        doc.AddItem(FontSize("+2", template_list))
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format(bgcolor='#ffffff')
        return

    try:
        if cgidata.keys():
            ChangeHTML(mlist, cgidata, template_name, doc)
        FormatHTML(mlist, doc, template_name, template_info)
    finally:
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format(bgcolor='#ffffff')



def FormatHTML(mlist, doc, template_name, template_info):
    doc.AddItem(Header(1,'%s:' % mlist.real_name))
    doc.AddItem(Header(1, template_info))
    doc.AddItem('<hr>')

    link = Link(mlist.GetScriptURL('admin'),
                _('View or edit the list configuration information.'))

    doc.AddItem(FontSize("+1", link))
    doc.AddItem('<p>')
    doc.AddItem('<hr>')
    form = Form(mlist.GetScriptURL('edithtml') + '/' + template_name)
    text = Utils.QuoteHyperChars(mlist.SnarfHTMLTemplate(template_name))
    form.AddItem(TextArea('html_code', text, rows=40, cols=75))
    form.AddItem('<p>' + _('When you are done making changes...'))
    form.AddItem(SubmitButton('submit', _('Submit Changes')))
    doc.AddItem(form)



def ChangeHTML(mlist, cgi_info, template_name, doc):
    if not cgi_info.has_key('html_code'):
        doc.AddItem(Header(3,_("Can't have empty html page.")))
        doc.AddItem(Header(3,_("HTML Unchanged.")))
        doc.AddItem('<hr>')
        return
    code = cgi_info['html_code'].value
    f = open(os.path.join(mlist._template_dir, mlist.preferred_language,
                          template_name),
             'w')
    f.write(code)
    f.close()
    doc.AddItem(Header(3, _('HTML successfully updated.')))
    doc.AddItem('<hr>')
