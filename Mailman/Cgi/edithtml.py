#! /usr/bin/env python
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

"""Script which implements admin editing of the list's html templates."""

import sys
import os, cgi, string, types
from Mailman import Utils, MailList
from Mailman import htmlformat
from Mailman.HTMLFormatter import HTMLFormatter
from Mailman import Errors


#Editable templates.  We should also be able to edit the archive index, which 
#currently isn't a working template, but will be soon.

def main():
    # XXX: blech, yuck, ick
    global doc
    global list
    global template_info
    global template_name

    template_data = (('listinfo.html',    'General list information page'),
                     ('subscribe.html',   'Subscribe results page'),
                     ('options.html',     'User specific options page'),
                     ('handle_opts.html', 'Changing user options results page'),
                     ('archives.html',    'Archives index page')
                    )


    doc = InitDocument()

    path = os.environ['PATH_INFO']
    list_info = Utils.GetPathPieces(path)

    if len(list_info) < 1:
        doc.AddItem(htmlformat.Header(2, "Invalid options to CGI script."))
        print doc.Format()
        sys.exit(0)

    list_name = string.lower(list_info[0])

    try:
        list = MailList.MailList(list_name, lock=0)
    except:
        doc.AddItem(htmlformat.Header(2, "%s : No such list" % list_name))
        print doc.Format()
        sys.exit(0)

    if not list._ready:
        doc.AddItem(htmlformat.Header(2, "%s : No such list" % list_name))
        print doc.Format()
        sys.exit(0)
    #
    # get the list._template_dir attribute
    #
    HTMLFormatter.InitVars(list)

    if len(list_info) > 1:
        template_name = list_info[1]
        for (template, info) in template_data:
            if template == template_name:
                template_info = info
                doc.SetTitle('%s -- Edit html for %s' % 
                             (list.real_name, template_info)) 
                break
        else:
            doc.SetTitle('Edit HTML : Error')
            doc.AddItem(htmlformat.Header(2, "%s: Invalid template" % template_name))
            doc.AddItem(list.GetMailmanFooter())
            print doc.Format()
            sys.exit(0)
    else:
        doc.SetTitle('%s -- HTML Page Editing' % list.real_name)
        doc.AddItem(htmlformat.Header(1, '%s -- HTML Page Editing' % list.real_name))
        doc.AddItem(htmlformat.Header(2, 'Select page to edit:'))
        template_list = htmlformat.UnorderedList()
        for (template, info) in template_data:
            l = htmlformat.Link("%s/%s" % (list.GetRelativeScriptURL('edithtml'),template),
                                info)
            template_list.AddItem(l)
        doc.AddItem(htmlformat.FontSize("+2", template_list))
        doc.AddItem(list.GetMailmanFooter())
        print doc.Format()
        sys.exit(0)

    try:
        cgi_data = cgi.FieldStorage()
        if len(cgi_data.keys()):
            if not cgi_data.has_key('adminpw'):
                m = 'Error: You must supply the admin password to edit html.'
                doc.AddItem(htmlformat.Header(3,
                                              htmlformat.Italic(
                                                  htmlformat.FontAttr(
                                                      m, color="ff5060"))))
                doc.AddItem('<hr>')
            else:
                try:
                    list.ConfirmAdminPassword(cgi_data['adminpw'].value)
                    ChangeHTML(list, cgi_data, template_name, doc)
                except Errors.MMBadPassword:
                    m = 'Error: Incorrect admin password.'
                    doc.AddItem(htmlformat.Header(3, 
                                                  htmlformat.Italic(
                                                      htmlformat.FontAttr(
                                                          m, color="ff5060"))))
                    doc.AddItem('<hr>')



        FormatHTML(doc)

    finally:
        try:
            doc.AddItem(list.GetMailmanFooter())
            print doc.Format()
        except:
            pass



def InitDocument():
    return htmlformat.HeadlessDocument()


def FormatHTML(doc):
    # XXX: blech, yuck, ick
    global list
    global template_info
    global template_name

    doc.AddItem(htmlformat.Header(1,'%s:' % list.real_name))
    doc.AddItem(htmlformat.Header(1, template_info))

    doc.AddItem('<hr>')

    link = htmlformat.Link(list.GetRelativeScriptURL('admin'),
			   'View or edit the list configuration information.')
    doc.AddItem(htmlformat.FontSize("+1", link))
    doc.AddItem('<p>')

    doc.AddItem('<hr>')

    form = htmlformat.Form("%s/%s" % (list.GetRelativeScriptURL('edithtml'),
                                      template_name))
    doc.AddItem(form)

    password_table = htmlformat.Table()
    password_table.AddRow(['Enter the admin password to edit html:',
			   htmlformat.PasswordBox('adminpw')])
    password_table.AddRow(['When you are done making changes...', 
			   htmlformat.SubmitButton('submit', 'Submit Changes')])

    form.AddItem(password_table)

    text = Utils.QuoteHyperChars(list.SnarfHTMLTemplate(template_name))
    form.AddItem(htmlformat.TextArea('html_code', text, rows=40, cols=75))


def ChangeHTML(list, cgi_info, template_name, doc):
    if not cgi_info.has_key('html_code'):
	doc.AddItem(htmlformat.Header(3,"Can't have empty html page."))
	doc.AddItem(htmlformat.Header(3,"HTML Unchanged."))
	doc.AddItem('<hr>')
	return
    code = cgi_info['html_code'].value
    f = open(os.path.join(list._template_dir, template_name), 'w')
    f.write(code)
    f.close()
    doc.AddItem(htmlformat.Header(3, 'HTML successfully updated.'))
    doc.AddItem('<hr>')
    
