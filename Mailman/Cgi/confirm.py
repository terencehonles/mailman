# Copyright (C) 2001 by the Free Software Foundation, Inc.
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

"""Confirm a pending action via URL."""

import signal

from Mailman import mm_cfg
from Mailman import Errors
from Mailman import i18n
from Mailman import MailList
from Mailman import Pending
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog

# Set up i18n
_ = i18n._
i18n.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)



def main():
    doc = Document()
    doc.set_language(mm_cfg.DEFAULT_SERVER_LANGUAGE)

    parts = Utils.GetPathPieces()
    if not parts:
        bad_confirmation(doc)
        doc.AddItem(MailmanLogo())
        print doc.Format()
        return

    listname = parts[0].lower()
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        bad_confirmation(doc, _('No such list <em>%(listname)s</em>'))
        doc.AddItem(MailmanLogo())
        print doc.Format()
        syslog('error', 'No such list "%s": %s', listname, e)
        return

    # Set the language for the list
    i18n.set_language(mlist.preferred_language)
    doc.set_language(mlist.preferred_language)

    # See the comment in admin.py about the need for the signal handler.
    def sigterm_handler(signum, frame, mlist=mlist):
        mlist.Unlock()

    # Now dig out the cookie
    mlist.Lock()
    try:
        signal.signal(signal.SIGTERM, sigterm_handler)
        try:
            cookie = parts[1]
            data = mlist.ProcessConfirmation(cookie)
            success(mlist, doc, *data)
        except (Errors.MMBadConfirmation, IndexError):
            days = int(mm_cfg.PENDING_REQUEST_LIFE / mm_cfg.days(1) + 0.5)
            bad_confirmation(doc, _('''Invalid confirmation string.  Note that
            confirmation strings expire approximately %(days)s days after the
            initial subscription request.  If your confirmation has expired,
            please try to re-submit your subscription.'''))
        except Errors.MMNoSuchUserError:
            bad_confirmation(doc, _('''Invalid confirmation string.  It is
            possible that you are attempting to confirm a request for an
            address that has already been unsubscribed.'''))
        except Errors.MMNeedApproval:
            title = _('Awaiting moderator approval')
            doc.SetTitle(title)
            doc.AddItem(Header(3, Bold(FontAttr(title, size='+2'))))
            doc.AddItem(_("""\
            You have successfully confirmed your subscription request to the
            mailing list %(listname)s, however final approval is required from
            the list moderator before you will be subscribed.  Your request
            has been forwarded to the list moderator, and you will be notified
            of the moderator's decision."""))
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format()
        mlist.Save()
    finally:
        mlist.Unlock()



def bad_confirmation(doc, extra=''):
    title = _('Bad confirmation string')
    doc.SetTitle(title)
    doc.AddItem(Header(3, Bold(FontAttr(title, color='#ff0000', size='+2'))))
    doc.AddItem(extra)



def success(mlist, doc, op, addr, password=None, digest=None, lang=None):
    listname = mlist.real_name
    # Different title based on operation performed
    if op == Pending.SUBSCRIPTION:
        title = _('Subscription request confirmed')
    elif op == Pending.UNSUBSCRIPTION:
        title = _('Removal request confirmed')
        lang = mlist.GetPreferredLanguage(addr)
    elif op == Pending.CHANGE_OF_ADDRESS:
        title = _('Change of address confirmed')
    # Use the user's preferred language
    i18n.set_language(lang)
    doc.set_language(lang)
    # Now set the title and report the results
    doc.SetTitle(title)
    doc.AddItem(Header(3, Bold(FontAttr(title, size='+2'))))
    if op == Pending.SUBSCRIPTION:
        doc.AddItem(_('''\
        You have successfully confirmed your subscription request for
        "%(addr)s" to the %(listname)s mailing list.  A separate confirmation
        message will be sent to your email address, along with your password,
        and other useful information and links.'''))
    elif op == Pending.UNSUBSCRIPTION:
        doc.AddItem(_('''\
        You have successfully confirmed your removal request for "%(addr)s" to
        the %(listname)s mailing list.'''))
    elif op == Pending.CHANGE_OF_ADDRESS:
        doc.AddItem(_('''\
        You have successfully confirmed your change of address to "%(addr)s"
        for the %(listname)s mailing list.'''))
