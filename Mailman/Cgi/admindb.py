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

import os
import string
import types
import cgi
from errno import ENOENT

from Mailman import Utils, MailList, Errors
from Mailman.htmlformat import *
from Mailman import mm_cfg



def handle_no_list(doc, extra=''):
    doc.SetTitle('Mailman Admindb Error')
    doc.AddItem(Header(2, 'Mailman Admindb Error'))
    doc.AddItem(extra)
    doc.AddItem('You must specify a list name.  Here is the ')
    link = mm_cfg.DEFAULT_URL
    if link[-1] <> '/':
        link = link + '/'
    link = link + 'admin'
    doc.AddItem(Link(link, 'list of available mailing lists.'))
    print doc.Format(bgcolor="#ffffff")



def main():
    doc = Document()
    # figure out which list we're going to process
    try:
        path = os.environ['PATH_INFO']
    except KeyError:
        handle_no_list(doc)
        return
    # get URL components.  the list name should be the zeroth part
    parts = Utils.GetPathPieces(path)
    try:
        listname = string.lower(parts[0])
    except IndexError:
        handle_no_list(doc)
        return
    # now that we have the list name, create the list object
    try:
        mlist = MailList.MailList(listname)
    except (Errors.MMUnknownListError, Errors.MMListNotReady):
        handle_no_list(doc, 'No such list: <tt>%s</tt><p>' % listname)
        return
    #
    # now we must authorize the user to view this page, and if they are, to
    # handle both the printing of the current outstanding requests, and the
    # selected actions
    try:
        form = cgi.FieldStorage()
        # Authenticate.
        is_auth = 0
        adminpw = None
        message = ''
        # has the user already authenticated?
        if form.has_key('adminpw'):
            adminpw = form['adminpw'].value
        try:
            # admindb uses the same cookie as admin
            is_auth = mlist.WebAuthenticate(password=adminpw, cookie='admin')
        except Errors.MMBadPasswordError:
            message = 'Sorry, wrong password.  Try again.'
        except Errors.MMExpiredCookieError:
            message = 'Your cookie has gone stale, ' \
                      'enter password to get a new one.',
        except Errors.MMInvalidCookieError:
            message = 'Error decoding authorization cookie.'
        except Errors.MMAuthenticationError:
            message = 'Authentication error.'
        #
        # Not authorized, so give them a chance to head over to the login page
        if not is_auth:
            uri = '/mailman/admindb%s/%s' % (mm_cfg.CGIEXT, listname)
            if message:
                message = FontAttr(
                    message, color='FF5060', size='+1').Format()
            print 'Content-type: text/html\n\n'
            text = Utils.maketext(
                'admlogin.txt',
                {'listname': listname,
                 'path'    : Utils.GetRequestURI(uri),
                 'message' : message,
                 })
            print text
            return
        #
        # If this is a form submission, then we'll process the requests and
        # print the results.  otherwise (there are no keys in the form), we'll
        # print out the list of pending requests
        #
        if len(form.keys()):
            doc.SetTitle("%s Admindb Results" % mlist.real_name)
            HandleRequests(mlist, doc, form)
        else:
            doc.SetTitle("%s Admindb" % mlist.real_name)
        PrintRequests(mlist, doc, form)
        text = doc.Format(bgcolor="#ffffff")
        print text
    finally:
        mlist.Save()
        mlist.Unlock()



def PrintRequests(mlist, doc, form):
    # The only types of requests we know about are add member and post.
    # Anything else that might have gotten in here somehow we'll just ignore
    # (This should never happen unless someone is hacking at the code).
    doc.AddItem(Header(2, 'Administrative requests for mailing list: <em>' +
                       mlist.real_name + '</em>'))
    # short circuit for when there are no pending requests
    if not mlist.NumRequestsPending():
	doc.AddItem('There are no pending requests.  You can now ')
        doc.AddItem(
            Link(mlist.GetRelativeScriptURL('admin'),
                 Italic('view or edit the list configuration information.')))
	doc.AddItem(mlist.GetMailmanFooter())
	return

    doc.AddItem(Utils.maketext(
        'admindbpreamble.html', {'listname': mlist.real_name}, raw=1))
    doc.AddItem(
        Link(mlist.GetRelativeScriptURL('admin'),
             Italic('view or edit the list configuration information')))
    doc.AddItem('.<p>')
    form = Form(mlist.GetRelativeScriptURL('admindb'))
    doc.AddItem(form)
    form.AddItem(SubmitButton('submit', 'Submit All Data'))
    #
    # Add the subscription request section
    subpendings = mlist.GetSubscriptionIds()
    if subpendings:
        form.AddItem('<hr>')
	form.AddItem(Center(Header(2, 'Subscription Requests')))
	t = Table(border=2)
	t.AddRow([
	    Bold('Address'),
	    Bold('Your Decision'),
	    Bold('Reason for subscription refusal (optional)')
            ])
        for id in subpendings:
	    PrintAddMemberRequest(mlist, id, t)
	form.AddItem(t)
    # Post holds are now handled differently
    heldmsgs = mlist.GetHeldMessageIds()
    total = len(heldmsgs)
    if total:
        count = 1
        for id in heldmsgs:
            info = mlist.GetRecord(id)
            PrintPostRequest(mlist, id, info, total, count, form)
            count = count + 1
    form.AddItem('<hr>')
    form.AddItem(SubmitButton('submit', 'Submit All Data'))
    doc.AddItem(mlist.GetMailmanFooter())



def PrintAddMemberRequest(mlist, id, table):
    time, addr, passwd, digest = mlist.GetRecord(id)
    table.AddRow([addr,
                  RadioButtonArray(id, ('Refuse', 'Subscribe')),
                  TextBox('comment-%d' % id, size=30)
                  ])

def PrintPostRequest(mlist, id, info, total, count, form):
    ptime, sender, subject, reason, filename = info
    form.AddItem('<hr>')
    msg = 'Posting Held for Approval'
    if total <> 1:
        msg = msg + ' (%d of %d)' % (count, total)
    form.AddItem(Center(Header(2, msg)))
    try:
        fp = open(os.path.join(mm_cfg.DATA_DIR, filename))
        text = fp.read(mm_cfg.ADMINDB_PAGE_TEXT_LIMIT)
        fp.close()
    except IOError, (code, msg):
        if code == ENOENT:
            form.AddItem('<em>Message with id #%d was lost.' % id)
            form.AddItem('<p>')
            # TBD: kludge to remove id from requests.db.  value==2 means
            # discard the message.
            try:
                mlist.HandleRequest(id, 2, None)
            except Errors.LostHeldMessage:
                pass
            return
        raise
    t = Table(cellspacing=0, cellpadding=0)
    t.AddRow([Bold('From:'), sender])
    t.AddRow([Bold('Reason:'), reason])
    t.AddRow([Bold('Subject:'), subject])
    t.AddRow([
        Bold('Action:'),
        RadioButtonArray(id, ("Approve", "Reject", "Discard (eg, spam)"))
        ])
    t.AddRow([
	Bold('If you reject this post, explain (optional):'),
	TextArea('comment-%d' % id, rows=4, cols=60,
                 text=("Please do *not* post administrative requests"
                       " to the mailing list!  If you wish to subscribe,"
                       " visit %s or send a 'help' message to the"
                       " the request address, %s , for instructions"
                       % (mlist.GetAbsoluteScriptURL('listinfo'),
                          mlist.GetRequestEmail())))
        ])
    row, col = t.GetCurrentRowIndex(), t.GetCurrentCellIndex()
    t.AddCellInfo(row, col, colspan=3)
    t.AddRow([Bold('Message Excerpt:'),
              TextArea('fulltext-%d' % id, text, rows=10, cols=60)])
    row, col = t.GetCurrentRowIndex(), t.GetCurrentCellIndex()
    t.AddCellInfo(row, col, colspan=3)
    form.AddItem(t)
    form.AddItem('<p>')



def HandleRequests(mlist, doc, form):
    erroraddrs = []
    for k in form.keys():
        formv = form[k]
        if type(formv) == types.ListType:
            continue
        try:
            v = int(formv.value)
            request_id = int(k)
        except ValueError:
            continue
        # get the action comment/reason if present
        commentkey = 'comment-%d' % request_id
        comment = '[No reason given]'
        if form.has_key(commentkey):
            comment = form[commentkey].value
        #
        # handle the request id
        try:
            mlist.HandleRequest(request_id, v, comment)
        except (KeyError, Errors.LostHeldMessage):
            # that's okay, it just means someone else has already updated the
            # database, so just ignore this id
            continue
        except Errors.MMAlreadyAMember, v:
            erroraddrs.append(v)
    # save the list and print the results
    mlist.Save()
    doc.AddItem(Header(2, 'Database Updated...'))
    if erroraddrs:
        for addr in erroraddrs:
            doc.AddItem(`addr` + ' is already a member<br>')
