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

"""Produce and process the pending-approval items for a list."""

import sys
import os, cgi, string, types
from Mailman import Utils, MailList, Errors
from Mailman.htmlformat import *
from Mailman import Cookie
from Mailman import mm_cfg

# copied from admin.py
def isAuthenticated(mlist, password=None, SECRET="SECRET"):
    if password is not None:  # explicit login
        try:             
            mlist.ConfirmAdminPassword(password)
        except Errors.MMBadPasswordError:
            AddErrorMessage(doc, 'Error: Incorrect admin password.')
            return 0

        token = `hash(list_name)`
        c = Cookie.Cookie()
        cookie_key = list_name + "-admin"
        c[cookie_key] = token
        c[cookie_key]['expires'] = mm_cfg.ADMIN_COOKIE_LIFE
        print c                         # Output the cookie
        return 1
    if os.environ.has_key('HTTP_COOKIE'):
        c = Cookie.Cookie( os.environ['HTTP_COOKIE'] )
        if c.has_key(list_name + "-admin"):
	    if c[list_name + "-admin"].value == `hash(list_name)`:
		return 1
	    else:
		AddErrorMessage(doc, "error decoding authorization cookie")
		return 0
    return 0


def main():
    # XXX: Yuk, blech, ick
    global list
    global form
    global doc
    global list_name

    doc = Document()

    try:
        path = os.environ['PATH_INFO']
    except KeyError:
        doc.SetTitle("Admindb Error")
        doc.AddItem(
            Header(2, "You must specify what list you are intenting to visit"))
        print doc.Format(bgcolor="#ffffff")
        sys.exit(0)

    list_info = Utils.GetPathPieces(path)

    if len(list_info) < 1:
        doc.SetTitle("Admindb Error")
        doc.AddItem(eader(2, "Invalid options to CGI script."))
        print doc.Format(bgcolor="#ffffff")
        sys.exit(0)
    list_name = string.lower(list_info[0])

    try:
        list = MailList.MailList(list_name)
    except:
        msg = "%s: No such list." % list_name
        doc.SetTitle("Admindb Error - %s" % msg)
        doc.AddItem(Header(2, msg))
        print doc.Format(bgcolor="#ffffff")
        sys.exit(0)

    if not list._ready:
        msg = "%s: No such list." % list_name
        doc.SetTitle("Admindb Error - %s" % msg)
        doc.AddItem(Header(2, msg))
        print doc.Format(bgcolor="#ffffff")
        sys.exit(0)

    try:
        form = cgi.FieldStorage()

        # authenticate.  all copied from admin.py
        is_auth = 0
        if form.has_key('adminpw'):
            is_auth = isAuthenticated(list, form['adminpw'].value)
            message = FontAttr('Sorry, wrong password.  Try again.',
                               color='ff5060', size='+1').Format()
        else:
            is_auth = isAuthenticated(list)
            message = ''
        if not is_auth:
            defaulturi = '/mailman/admindb%s/%s' % (mm_cfg.CGIEXT, list_name)
            print 'Content-type: text/html\n\n'
            text = Utils.maketext(
                'admlogin.txt',
                {'listname': list_name,
                 'path'    : os.environ.get('REQUEST_URI', defaulturi),
                 'message' : message,
                 })
            print text
            return

        if len(form.keys()):
            doc.SetTitle("%s Admindb Results" % list.real_name)
            HandleRequests(doc)
        else:
            doc.SetTitle("%s Admindb" % list.real_name)
        PrintRequests(doc)
        text = doc.Format(bgcolor="#ffffff")
        print text
        sys.stdout.flush()
    finally:
        list.Unlock()



# Note, these 2 functions use i only to count the number of times to
# go around.  We always operate on the first element of the list
# because we're going to delete the element after we operate on it.

def SubscribeAll():
    # XXX: Yuk, blech, ick
    global list
    global form
    for i in range(len(list.requests['add_member'])):
	comment_key = 'comment-%d' % list.requests['add_member'][0][0]
	if form.has_key(comment_key):
	    list.HandleRequest(('add_member', 0), 1, form[comment_key].value)
	else:
	    list.HandleRequest(('add_member', 0), 1)

def SubscribeNone():
    # XXX: Yuk, blech, ick
    global list
    global form
    for i in range(len(list.requests['add_member'])):
	comment_key = 'comment-%d' % list.requests['add_member'][0][0]
	if form.has_key(comment_key):
	    list.HandleRequest(('add_member', 0), 0, form[comment_key].value)
	else:
	    list.HandleRequest(('add_member', 0), 0)

def PrintHeader(str, error=0):
    # XXX: blech, yuk, ick
    global doc

    if error:
	it = FontAttr(str, color="ff5060")
    else:
	it = str
    doc.AddItem(Header(3, Italic(it)))
    doc.AddItem('<hr>')


def HandleRequests(doc):
    # XXX: Yuk, blech, ick
    global list
    global form
##     if not form.has_key('adminpw'):
##	PrintHeader('You need to supply the admin password '
##		    'to answer requests.', error=1)
##	return
##    try:
##	list.ConfirmAdminPassword(form['adminpw'].value)
##    except:
##	PrintHeader('Incorrect admin password.', error=1)
##	return
    ignore_subscribes = 0
    if form.has_key('subscribe_all'):
	ignore_subscribes = 1
	SubscribeAll()
    elif form.has_key('subscribe_none'):
	ignore_subscribes = 1
	SubscribeNone()
    for k in form.keys():
        formv = form[k]
        if type(formv) == types.ListType:
            continue
        try:
            v = int(formv.value)
            request_id = int(k)
        except ValueError:
            continue
	try:
	    request = list.GetRequest(request_id)
	except Errors.MMBadRequestId:
	    continue # You've already changed the database.  No biggie.
	if ignore_subscribes and request[0] == 'add_member':
	    # We already handled this request.
	    continue
	comment_key = 'comment-%d' % request_id
	if form.has_key(comment_key):
	    list.HandleRequest(request, v, form[comment_key].value)
	else:
	    list.HandleRequest(request, v)
    list.Save()
    PrintHeader('Database Updated...')


def PrintAddMemberRequest(val, table):
    table.AddRow([
	val[3], 
	RadioButtonArray(val[0], ("Refuse", "Subscribe")),
	TextBox("comment-%d" % val[0], size=50)
	])

def PrintPostRequest(val, form):
    t = Table(cellspacing=10)
    t.AddRow([
        FontSize("+1", Bold('Post held because: ')),
        val[3]
        ])
    t.AddRow([
	FontSize("+1", Bold('Action to take on this post:')),
	RadioButtonArray(val[0], ("Approve", "Reject", "Discard (eg, spam)")),
	SubmitButton('submit', 'Submit All Data')
        ])
    t.AddRow([
	FontSize("+1", Bold('If you reject this post, explain (optional):')),
	TextBox("comment-%d" % val[0], size=50)
        ])

    cur_row = t.GetCurrentRowIndex()
    cur_col = t.GetCurrentCellIndex()
    t.AddCellInfo(cur_row, cur_col, colspan=3)

    t.AddRow([
	FontSize("+1", Bold('Contents:'))
        ])
    form.AddItem(t)
    form.AddItem(Preformatted(val[2][1]))
    form.AddItem('<p>')



def PrintRequests(doc):
    # XXX: Yuk, blech, ick
    global list
    global form

    # The only types of requests we know about are add_member and post.
    # Anything else that might have gotten in here somehow we'll just
    # ignore (This should never happen unless someone is hacking at
    # the code).

    doc.AddItem(Header(2, "Administrative requests for '%s' mailing list"
                       % list.real_name))
    doc.AddItem(FontSize("+1",
                         Link(list.GetRelativeScriptURL('admin'),
                              Italic(
        'View or edit the list configuration information'))))
    doc.AddItem('<p>')
    if not list.NumRequestsPending():
	doc.AddItem(Header(3,'There are no pending requests.'))
	doc.AddItem(list.GetMailmanFooter())
	return
    form = Form(list.GetRelativeScriptURL('admindb'))
    doc.AddItem(form)
##    form.AddItem('Admin password: ')
##    form.AddItem(PasswordBox('adminpw'))
##    form.AddItem('<p>')
    if list.requests.has_key('add_member'):
##	form.AddItem('<hr>')
## 	t = Table(cellspacing=10)
## 	t.AddRow([
## 	    SubmitButton('submit', 'Submit All Data'),
## 	    SubmitButton('subscribe_all', 'Subscribe Everybody'),
## 	    SubmitButton('subscribe_none', 'Refuse Everybody')
## 	    ])
## 	form.AddItem(t)
##	form.AddItem('<hr>')
	form.AddItem(Center(
	    Header(2, 'Subscription Requests')))
	t = Table(border=2)
	t.AddRow([
	    Bold('Email'),
	    Bold('Decision'),
	    Bold('Reasoning for subscription refusal (optional)')
            ])
	for request in list.requests['add_member']:
	    PrintAddMemberRequest(request, t)

	form.AddItem(t)
	t = Table(cellspacing=10)
	t.AddRow([
	    SubmitButton('submit', 'Submit All Data'),
	    SubmitButton('subscribe_all', 'Subscribe Everybody'),
	    SubmitButton('subscribe_none', 'Refuse Everybody')
	    ])
	form.AddItem(t)

	# Print submitit buttons...
    if list.requests.has_key('post'):
	for request in list.requests['post']:
	    form.AddItem('<hr>')
	    form.AddItem(Center(Header(2,
                                                             "Held Message")))
	    PrintPostRequest(request, form)
    doc.AddItem(list.GetMailmanFooter())


# copied from admin.py
def AddErrorMessage(doc, errmsg, *args):
    doc.AddItem(Header(3, Italic(FontAttr(errmsg % args, color="#ff66cc"))))
