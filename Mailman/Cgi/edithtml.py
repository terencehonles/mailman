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

"""Script which implements admin editing of the list's html templates."""

import sys
import os
import cgi
import string

from Mailman import Utils
from Mailman import MailList
from Mailman.htmlformat import *
from Mailman.HTMLFormatter import HTMLFormatter
from Mailman import Errors



def main():
    template_data = (
        ('listinfo.html',    'General list information page'),
        ('subscribe.html',   'Subscribe results page'),
        ('options.html',     'User specific options page'),
        ('handle_opts.html', 'Changing user options results page'),
        )

    doc = Document()

    path = os.environ['PATH_INFO']
    parts = Utils.GetPathPieces(path)

    if len(parts) < 1:
        doc.AddItem(Header(2, "List name is required."))
        print doc.Format(bgcolor='#ffffff')
        return

    listname = string.lower(parts[0])
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        doc.AddItem(Header(2, 'No such list <em>%s</em>' % listname))
        print doc.Format(bgcolor='#ffffff')
        sys.stderr.write('No such list "%s": %s\n' % (listname, e))
        return

    # get the list._template_dir attribute
    HTMLFormatter.InitVars(mlist)

    if len(parts) > 1:
        template_name = parts[1]
        for (template, info) in template_data:
            if template == template_name:
                template_info = info
                doc.SetTitle('%s -- Edit html for %s' % 
                             (mlist.real_name, template_info)) 
                break
        else:
            doc.SetTitle('Edit HTML : Error')
            doc.AddItem(Header(2, "%s: Invalid template" % template_name))
            doc.AddItem(mlist.GetMailmanFooter())
            print doc.Format(bgcolor='#ffffff')
            return
    else:
        doc.SetTitle('%s -- HTML Page Editing' % mlist.real_name)
        doc.AddItem(Header(1, '%s -- HTML Page Editing' % mlist.real_name))
        doc.AddItem(Header(2, 'Select page to edit:'))
        template_list = UnorderedList()
        for (template, info) in template_data:
            l = Link(mlist.GetRelativeScriptURL('edithtml') + '/' + template,
                     info)
            template_list.AddItem(l)
        doc.AddItem(FontSize("+2", template_list))
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format(bgcolor='#ffffff')
        return

    try:
        cgi_data = cgi.FieldStorage()
        if len(cgi_data.keys()):
            if not cgi_data.has_key('adminpw'):
                m = 'Error: You must supply the admin password to edit html.'
                doc.AddItem(Header(3, Italic(FontAttr(m, color="ff5060"))))
                doc.AddItem('<hr>')
            else:
                try:
                    mlist.ConfirmAdminPassword(cgi_data['adminpw'].value)
                    ChangeHTML(mlist, cgi_data, template_name, doc)
                except Errors.MMBadPasswordError:
                    m = 'Error: Incorrect admin password.'
                    doc.AddItem(Header(3, Italic(FontAttr(m, color="ff5060"))))
                    doc.AddItem('<hr>')
        FormatHTML(mlist, doc, template_name, template_info)
    finally:
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format(bgcolor='#ffffff')



def FormatHTML(mlist, doc, template_name, template_info):
    doc.AddItem(Header(1,'%s:' % mlist.real_name))
    doc.AddItem(Header(1, template_info))
    doc.AddItem('<hr>')

    link = Link(mlist.GetRelativeScriptURL('admin'),
                'View or edit the list configuration information.')

    doc.AddItem(FontSize("+1", link))
    doc.AddItem('<p>')
    doc.AddItem('<hr>')
    form = Form(mlist.GetRelativeScriptURL('edithtml') + '/' + template_name)
    doc.AddItem(form)

    password_table = Table()
    password_table.AddRow(['Enter the admin password to edit html:',
			   PasswordBox('adminpw')])
    password_table.AddRow(['When you are done making changes...', 
			   SubmitButton('submit', 'Submit Changes')])

    form.AddItem(password_table)
    text = Utils.QuoteHyperChars(mlist.SnarfHTMLTemplate(template_name))
    form.AddItem(TextArea('html_code', text, rows=40, cols=75))



def ChangeHTML(mlist, cgi_info, template_name, doc):
    if not cgi_info.has_key('html_code'):
	doc.AddItem(Header(3,"Can't have empty html page."))
	doc.AddItem(Header(3,"HTML Unchanged."))
	doc.AddItem('<hr>')
	return
    code = cgi_info['html_code'].value
    f = open(os.path.join(mlist._template_dir, template_name), 'w')
    f.write(code)
    f.close()
    doc.AddItem(Header(3, 'HTML successfully updated.'))
    doc.AddItem('<hr>')
