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

"""Produce and process the pending-approval items for a list."""

import sys
import os
import types
import cgi
import errno
import signal

from mimelib.Parser import Parser
from mimelib.MsgReader import MsgReader
import mimelib.Errors

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman import Message
from Mailman import i18n
from Mailman.Cgi import Auth
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog

NL = '\n'

# Set up i18n.  Until we know which list is being requested, we use the
# server's default.
_ = i18n._
i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)



def main():
    # Figure out which list is being requested
    parts = Utils.GetPathPieces()
    if not parts:
        handle_no_list()
        return

    listname = parts[0].lower()
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        handle_no_list(doc, _('No such list <em>%(listname)s</em>'))
        syslog('error', 'No such list "%s": %s\n', listname, e)
        return

    # Now that we know which list to use, set the system's language to it.
    i18n.set_language(mlist.preferred_language)

    # Make sure the user is authorized to see this page.
    cgidata = cgi.FieldStorage()

    if not mlist.WebAuthenticate((mm_cfg.AuthListAdmin,
                                  mm_cfg.AuthListModerator,
                                  mm_cfg.AuthSiteAdmin),
                                 cgidata.getvalue('adminpw', '')):
        if cgidata.has_key('admlogin'):
            # This is a re-authorization attempt
            msg = Bold(FontSize('+1', _('Authorization failed.'))).Format()
        else:
            msg = ''
        Auth.loginpage(mlist, 'admindb', msg=msg)
        return

    # Set up the results document
    doc = Document()
    doc.set_language(mlist.preferred_language)
    
    # We need a signal handler to catch the SIGTERM that can come from Apache
    # when the user hits the browser's STOP button.  See the comment in
    # admin.py for details.
    #
    # BAW: Strictly speaking, the list should not need to be locked just to
    # read the request database.  However the request database asserts that
    # the list is locked in order to load it and it's not worth complicating
    # that logic.
    def sigterm_handler(signum, frame, mlist=mlist):
        # Make sure the list gets unlocked...
        mlist.Unlock()
        # ...and ensure we exit, otherwise race conditions could cause us to
        # enter MailList.Save() while we're in the unlocked state, and that
        # could be bad!
        sys.exit(0)

    mlist.Lock()
    try:
        # Install the emergency shutdown signal handler
        signal.signal(signal.SIGTERM, sigterm_handler)

        realname = mlist.real_name
        if not cgidata.keys():
            # If this is not a form submission (i.e. there are no keys in the
            # form), then all we don't need to do much special.
            doc.SetTitle(_('%(realname)s Administrative Database'))
        else:
            # This is a form submission
            doc.SetTitle(_('%(realname)s Administrative Database Results'))
            process_form(mlist, doc, cgidata)
        # Now print the results and we're done
        show_requests(mlist, doc)
        mlist.Save()
    finally:
        mlist.Unlock()

    print doc.Format()



def handle_no_list(msg=''):
    # Print something useful if no list was given.
    doc = Document()
    doc.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)

    header = _('Mailman Administrative Database Error')
    doc.SetTitle(header)
    doc.AddItem(Header(2, header))
    doc.AddItem(msg)
    url = Utils.ScriptURL('admin', absolute=1)
    link = Link(url, _('list of available mailing lists.')).Format()
    doc.AddItem(_('You must specify a list name.  Here is the %(link)s'))
    doc.AddItem('<hr>')
    doc.AddItem(MailmanLogo())
    print doc.Format()



def show_requests(mlist, doc):
    # Print all the requests outstanding in the database.  The only ones we
    # know about are subscription and post requests.  Anything else that might
    # have gotten in here somehow we'll just ignore (This should never happen
    # unless someone is hacking at the code).
    doc.AddItem(Header(2, _('Administrative requests for mailing list:')
                       + ' <em>%s</em>' % mlist.real_name))
    # Short circuit for when there are no pending requests
    if not mlist.NumRequestsPending():
        doc.AddItem(_('There are no pending requests.'))
        doc.AddItem(mlist.GetMailmanFooter())
        return

    # Add the preamble template
    doc.AddItem(Utils.maketext(
        'admindbpreamble.html',
        {'listname': mlist.real_name},
        raw=1, mlist=mlist))

    # Form submits back to this script
    form = Form(mlist.GetScriptURL('admindb'))
    doc.AddItem(form)
    form.AddItem(SubmitButton('submit', _('Submit All Data')))
    # Add the subscription request section
    subpendings = mlist.GetSubscriptionIds()
    if subpendings:
        form.AddItem('<hr>')
        form.AddItem(Center(Header(2, _('Subscription Requests'))))
        table = Table(border=2)
        table.AddRow([Center(Bold(_('Address'))),
                      Center(Bold(_('Your Decision'))),
                      Center(Bold(_('Reason for refusal')))
                      ])
        for id in subpendings:
            time, addr, passwd, digest, lang = mlist.GetRecord(id)
            table.AddRow([addr,
                          RadioButtonArray(id, (_('Defer'),
                                                _('Approve'),
                                                _('Reject'),
                                                _('Discard')),
                                           values=(mm_cfg.DEFER,
                                                   mm_cfg.SUBSCRIBE,
                                                   mm_cfg.REJECT,
                                                   mm_cfg.DISCARD),
                                           checked=0),
                          TextBox('comment-%d' % id, size=45)
                          ])
        form.AddItem(table)
    # Post holds are handled differently
    heldmsgs = mlist.GetHeldMessageIds()
    total = len(heldmsgs)
    if total:
        count = 1
        for id in heldmsgs:
            info = mlist.GetRecord(id)
            show_post_requests(mlist, id, info, total, count, form)
            count += 1
    form.AddItem('<hr>')
    form.AddItem(SubmitButton('submit', _('Submit All Data')))
    doc.AddItem(mlist.GetMailmanFooter())



def show_post_requests(mlist, id, info, total, count, form):
    # For backwards compatibility with pre 2.0beta3
    if len(info) == 5:
        ptime, sender, subject, reason, filename = info
        msgdata = {}
    else:
        ptime, sender, subject, reason, filename, msgdata = info
    form.AddItem('<hr>')
    # Header shown on each held posting (including count of total)
    msg = _('Posting Held for Approval')
    if total <> 1:
        msg += _(' (%(count)d of %(total)d)')
    form.AddItem(Center(Header(2, msg)))
    # We need to get the headers and part of the textual body of the message
    # being held.  The best way to do this is to use the mimelib Parser to get
    # an actual object, which will be easier to deal with.  We probably could
    # just do raw reads on the file.
    p = Parser(Message.Message)
    try:
        fp = open(os.path.join(mm_cfg.DATA_DIR, filename))
        msg = p.parse(fp)
        fp.close()
    except IOError, e:
        if e.code <> errno.ENOENT:
            raise
        form.AddItem(_('<em>Message with id #%(id)d was lost.'))
        form.AddItem('<p>')
        # BAW: kludge to remove id from requests.db.
        try:
            mlist.HandleRequest(id, mm_cfg.DISCARD)
        except Errors.LostHeldMessage:
            pass
        return
    except mimelib.Errors.MessageParseError:
        form.AddItem(_('<em>Message with id #%(id)d is corrupted.'))
        # BAW: Should we really delete this, or shuttle it off for site admin
        # to look more closely at?
        form.AddItem('<p>')
        # BAW: kludge to remove id from requests.db.
        try:
            mlist.HandleRequest(id, mm_cfg.DISCARD)
        except Errors.LostHeldMessage:
            pass
        return
    # Get the header text and the message body excerpt
    lines = []
    chars = 0
    reader = MsgReader(msg)
    while 1:
        line = reader.readline()
        if not line:
            break
        lines.append(line)
        chars += len(line)
        if chars > mm_cfg.ADMINDB_PAGE_TEXT_LIMIT:
            break
    body = NL.join(lines)[:mm_cfg.ADMINDB_PAGE_TEXT_LIMIT]
    hdrtxt = NL.join(['%s: %s' % (k, v) for k, v in msg.items()])

    # Okay, we've reconstituted the message just fine.  Now for the fun part!
    t = Table(cellspacing=0, cellpadding=0, width='100%')
    t.AddRow([Bold(_('From:')), sender])
    row, col = t.GetCurrentRowIndex(), t.GetCurrentCellIndex()
    t.AddCellInfo(row, col-1, align='right')
    t.AddRow([Bold(_('Subject:')), cgi.escape(subject)])
    t.AddCellInfo(row+1, col-1, align='right')
    t.AddRow([Bold(_('Reason:')), reason])
    t.AddCellInfo(row+2, col-1, align='right')
    # We can't use a RadioButtonArray here because horizontal placement can be
    # confusing to the user and vertical placement takes up too much
    # real-estate.  This is a hack!
    buttons = Table(cellspacing="5", cellpadding="0")
    buttons.AddRow(map(lambda x, s='&nbsp;'*5: s+x+s,
                       (_('Defer'), _('Approve'), _('Reject'), _('Discard'))))
    buttons.AddRow([Center(RadioButton(id, mm_cfg.DEFER, 1)),
                    Center(RadioButton(id, mm_cfg.APPROVE, 0)),
                    Center(RadioButton(id, mm_cfg.REJECT, 0)),
                    Center(RadioButton(id, mm_cfg.DISCARD, 0)),
                    ])
    t.AddRow([Bold(_('Action:')), buttons])
    t.AddCellInfo(row+3, col-1, align='right')
    t.AddRow(['&nbsp;',
              CheckBox('preserve-%d' % id, 'on', 0).Format() +
              '&nbsp;' + _('Preserve message for site administrator')
              ])
    t.AddRow(['&nbsp;',
              CheckBox('forward-%d' % id, 'on', 0).Format() +
              '&nbsp;' + _('Additionally, forward this message to: ') +
              TextBox('forward-addr-%d' % id, size=47,
                      value=mlist.GetOwnerEmail()).Format()
              ])
    t.AddRow([
        Bold(_('If you reject this post,<br>please explain (optional):')),
        TextArea('comment-%d' % id, rows=4, cols=80,
                 text = Utils.wrap(msgdata.get('rejection-notice',
                                               _('[No explanation given]')),
                                   column=80))
        ])
    row, col = t.GetCurrentRowIndex(), t.GetCurrentCellIndex()
    t.AddCellInfo(row, col-1, align='right')
    t.AddRow([Bold(_('Message Headers:')),
              TextArea('headers-%d' % id, hdrtxt,
                       rows=10, cols=80)])
    row, col = t.GetCurrentRowIndex(), t.GetCurrentCellIndex()
    t.AddCellInfo(row, col-1, align='right')
    t.AddRow([Bold(_('Message Excerpt:')),
              TextArea('fulltext-%d' % id, body, rows=10, cols=80)])
    t.AddCellInfo(row+1, col-1, align='right')
    form.AddItem(t)
    form.AddItem('<p>')



def process_form(mlist, doc, cgidata):
    # Process the form and make updates to the admin database.
    erroraddrs = []
    for k in cgidata.keys():
        formv = cgidata[k]
        if type(formv) == types.ListType:
            continue
        try:
            v = int(formv.value)
            request_id = int(k)
        except ValueError:
            continue
        # Get the action comment and reasons if present.
        commentkey = 'comment-%d' % request_id
        preservekey = 'preserve-%d' % request_id
        forwardkey = 'forward-%d' % request_id
        forwardaddrkey = 'forward-addr-%d' % request_id
        # Defaults
        comment = _('[No reason given]')
        preserve = 0
        forward = 0
        forwardaddr = ''
        if cgidata.has_key(commentkey):
            comment = cgidata[commentkey].value
        if cgidata.has_key(preservekey):
            preserve = cgidata[preservekey].value
        if cgidata.has_key(forwardkey):
            forward = cgidata[forwardkey].value
        if cgidata.has_key(forwardaddrkey):
            forwardaddr = cgidata[forwardaddrkey].value
        # Handle the request id
        try:
            mlist.HandleRequest(request_id, v, comment,
                                preserve, forward, forwardaddr)
        except (KeyError, Errors.LostHeldMessage):
            # That's okay, it just means someone else has already updated the
            # database while we were staring at the page, so just ignore it
            continue
        except Errors.MMAlreadyAMember, v:
            erroraddrs.append(v)
    # save the list and print the results
    doc.AddItem(Header(2, _('Database Updated...')))
    if erroraddrs:
        for addr in erroraddrs:
            doc.AddItem(`addr` + _(' is already a member') + '<br>')
