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

"""Produce user options form, from options.html template.

Takes listname/userid in PATH_INFO, expecting an `obscured' userid.  Depending
on the Utils.{O,Uno}bscureEmail utilities tolerance, will work fine with an
unobscured ids as well.

"""

# We don't need to lock in this script, because we're never going to change
# data. 

import sys
import os, string
from Mailman import Utils, MailList, htmlformat
from Mailman import mm_cfg
from Mailman import Errors

def main():
    doc = htmlformat.HeadlessDocument()
    try:
        path = os.environ['PATH_INFO']
    except KeyError:
        path = ""
    list_info = Utils.GetPathPieces(path)
    # sanity check options
    if len(list_info) < 2:
        doc.AddItem(htmlformat.Header(2, "Error"))
        doc.AddItem(htmlformat.Bold("Invalid options to CGI script."))
        print doc.Format()
        sys.exit(0)
    # get the list and user's name
    list_name = string.lower(list_info[0])
    user = Utils.UnobscureEmail(list_info[1])
    # open list
    try:
        mlist = MailList.MailList(list_name, lock=0)
    except Errors.MMUnknownListError:
        doc.AddItem(htmlformat.Header(2, "Error"))
        doc.AddItem(htmlformat.Bold("%s: No such list." % list_name ))
        print doc.Format()
        sys.exit(0)
    # more list sanity checking
    if not mlist._ready:
        doc.AddItem(htmlformat.Header(2, "Error"))
        doc.AddItem(htmlformat.Bold("%s: No such list." % list_name ))
        print doc.Format()
        sys.exit(0)
    # Sanity check the user
    user = Utils.LCDomain(user)
    if not mlist.members.has_key(user) \
       and not mlist.digest_members.has_key(user):
        doc.AddItem(htmlformat.Header(2, "Error"))
        doc.AddItem(htmlformat.Bold("%s: No such member %s."
                                    % (list_name, `user`)))
        doc.AddItem(mlist.GetMailmanFooter())
        print doc.Format()
        sys.exit(0)
    # find the case preserved email address (the one the user subscribed with)
    cpuser = mlist.members.get(mlist.FindUser(user))
    if cpuser <> 0:
        user = user + ' (' + cpuser + ')'
    # Re-obscure the user's address for the page banner if obscure_addresses
    # set.
    if mlist.obscure_addresses:
        presentable_user = Utils.ObscureEmail(user, for_text=1)
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
        mm_cfg.AcknowlegePosts, 0, user)
    replacements['<mm-ack-posts-button>'] = mlist.FormatOptionButton(
        mm_cfg.AcknowlegePosts, 1, user)
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
    doc.AddItem(mlist.ParseTags('options.html', replacements))
    print doc.Format()
