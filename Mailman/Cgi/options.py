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

"""Produce user options form, from options.html template.

Takes listname/userid in PATH_INFO, expecting an `obscured' userid.  Depending
on the Utils.{O,Uno}bscureEmail utilities tolerance, will work fine with an
unobscured ids as well.

"""

# We don't need to lock in this script, because we're never going to change
# data. 

import os
import string

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import MailList
from Mailman import Errors
from Mailman.htmlformat import *
from Mailman.Logging.Syslog import syslog



def main():
    doc = HeadlessDocument()
    try:
        path = os.environ['PATH_INFO']
    except KeyError:
        path = ''

    parts = Utils.GetPathPieces(path)
    # sanity check options
    if len(parts) < 2:
        doc.AddItem(Header(2, "Error"))
        doc.AddItem(Bold("Invalid options to CGI script."))
        print doc.Format()
        return

    # get the list and user's name
    listname = string.lower(parts[0])
    user = Utils.UnobscureEmail(parts[1])
    # open list
    try:
        mlist = MailList.MailList(listname, lock=0)
    except Errors.MMListError, e:
        doc.AddItem(Header(2, "Error"))
        doc.AddItem(Bold('No such list <em>%s</em>' % listname))
        print doc.Format()
        syslog('No such list "%s": %s\n' % (listname, e))
        return

    # Sanity check the user
    user = Utils.LCDomain(user)
    if not mlist.members.has_key(user) and \
            not mlist.digest_members.has_key(user):
        # then
        doc.AddItem(Header(2, "Error"))
        doc.AddItem(Bold("%s: No such member %s." % (listname, `user`)))
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format()
        return

    # find the case preserved email address (the one the user subscribed with)
    lcuser = mlist.FindUser(user)
    cpuser = mlist.GetUserSubscribedAddress(lcuser)
    if lcuser == cpuser:
        cpuser = None
    if mlist.obscure_addresses:
        presentable_user = Utils.ObscureEmail(user, for_text=1)
        if cpuser is not None:
            cpuser = Utils.ObscureEmail(cpuser, for_text=1)
    else:
        presentable_user = user

    # Do replacements
    replacements = mlist.GetStandardReplacements()
    replacements['<mm-digest-radio-button>'] = mlist.FormatOptionButton(
        mm_cfg.Digests, 1, user)
    replacements['<mm-undigest-radio-button>'] = mlist.FormatOptionButton(
        mm_cfg.Digests, 0, user)
    replacements['<mm-plain-digests-button>'] = mlist.FormatOptionButton(
        mm_cfg.DisableMime, 1, user)
    replacements['<mm-mime-digests-button>'] = mlist.FormatOptionButton(
        mm_cfg.DisableMime, 0, user)
    replacements['<mm-delivery-enable-button>'] = mlist.FormatOptionButton(
        mm_cfg.DisableDelivery, 0, user)
    replacements['<mm-delivery-disable-button>'] = mlist.FormatOptionButton(
        mm_cfg.DisableDelivery, 1, user)
    replacements['<mm-disabled-notice>'] = mlist.FormatDisabledNotice(user)
    replacements['<mm-dont-ack-posts-button>'] = mlist.FormatOptionButton(
        mm_cfg.AcknowledgePosts, 0, user)
    replacements['<mm-ack-posts-button>'] = mlist.FormatOptionButton(
        mm_cfg.AcknowledgePosts, 1, user)
    replacements['<mm-receive-own-mail-button>'] = mlist.FormatOptionButton(
        mm_cfg.DontReceiveOwnPosts, 0, user)
    replacements['<mm-dont-receive-own-mail-button>'] = (
        mlist.FormatOptionButton(mm_cfg.DontReceiveOwnPosts, 1, user))
    replacements['<mm-public-subscription-button>'] = (
        mlist.FormatOptionButton(mm_cfg.ConcealSubscription, 0, user))
    replacements['<mm-hide-subscription-button>'] = mlist.FormatOptionButton(
        mm_cfg.ConcealSubscription, 1, user)
    replacements['<mm-digest-submit>'] = mlist.FormatButton(
        'setdigest', 'Submit My Changes')
    replacements['<mm-unsubscribe-button>'] = (
        mlist.FormatButton('unsub', 'Unsubscribe'))
    replacements['<mm-digest-pw-box>'] = mlist.FormatSecureBox('digpw')
    replacements['<mm-unsub-pw-box>'] = mlist.FormatSecureBox('upw')
    replacements['<mm-old-pw-box>'] = mlist.FormatSecureBox('opw')
    replacements['<mm-new-pass-box>'] = mlist.FormatSecureBox('newpw')
    replacements['<mm-confirm-pass-box>'] = mlist.FormatSecureBox('confpw')
    replacements['<mm-other-subscriptions-pw-box>'] = (
        mlist.FormatSecureBox('othersubspw'))
    replacements['<mm-other-subscriptions-submit>'] = (
        mlist.FormatButton('othersubs',
                           'List my other subscriptions'))
    replacements['<mm-change-pass-button>'] = (
        mlist.FormatButton('changepw', "Change My Password"))
    replacements['<mm-form-start>'] = (
        mlist.FormatFormStart('handle_opts', user))
    replacements['<mm-user>'] = user
    replacements['<mm-presentable-user>'] = presentable_user
    replacements['<mm-email-my-pw>'] = mlist.FormatButton('emailpw',
                                                          ('Email My Password'
                                                           ' To Me'))
    replacements['<mm-umbrella-notice>'] = (
        mlist.FormatUmbrellaNotice(user, "password"))

    if cpuser is not None:
        replacements['<mm-case-preserved-user>'] = '''
You are subscribed to this list with the case-preserved address
<em>%s</em>.''' % cpuser
    else:
        replacements['<mm-case-preserved-user>'] = ''

    doc.AddItem(mlist.ParseTags('options.html', replacements))
    print doc.Format()
