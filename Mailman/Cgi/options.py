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

"""Produce user options form, from list options.html template.

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

def main():
    doc = htmlformat.HeadlessDocument()

    try:
        path = os.environ['PATH_INFO']
    except KeyError:
        path = ""
    list_info = Utils.GetPathPieces(path)

    if len(list_info) < 2:
        doc.AddItem(htmlformat.Header(2, "Error"))
        doc.AddItem(htmlformat.Bold("Invalid options to CGI script."))
        print doc.Format()
        sys.exit(0)

    list_name = string.lower(list_info[0])
    user = Utils.UnobscureEmail(list_info[1])

    try:
      list = MailList.MailList(list_name, lock=0)
    except:
      doc.AddItem(htmlformat.Header(2, "Error"))
      doc.AddItem(htmlformat.Bold("%s: No such list." % list_name ))
      print doc.Format()
      sys.exit(0)

    if not list._ready:
        doc.AddItem(htmlformat.Header(2, "Error"))
        doc.AddItem(htmlformat.Bold("%s: No such list." % list_name ))
        print doc.Format()
        sys.exit(0)

    if string.lower(user) not in list.members + list.digest_members:
        doc.AddItem(htmlformat.Header(2, "Error"))
        doc.AddItem(htmlformat.Bold("%s: No such member %s."
                                    % (list_name, `user`)))
        doc.AddItem(list.GetMailmanFooter())
        print doc.Format()
        sys.exit(0)

    # Re-obscure the user's address for the page banner if obscure_addresses set.
    if list.obscure_addresses:
        presentable_user = Utils.ObscureEmail(user, for_text=1)
    else:
        presentable_user = user

    replacements = list.GetStandardReplacements()
    replacements['<mm-digest-radio-button>'] = list.FormatOptionButton(
            mm_cfg.Digests, 1, user)
    replacements['<mm-undigest-radio-button>'] = list.FormatOptionButton(
            mm_cfg.Digests, 0, user)
    replacements['<mm-plain-digests-button>'] = list.FormatOptionButton(
            mm_cfg.DisableMime, 1, user)
    replacements['<mm-mime-digests-button>'] = list.FormatOptionButton(
            mm_cfg.DisableMime, 0, user)
    replacements['<mm-delivery-enable-button>'] = list.FormatOptionButton(
            mm_cfg.DisableDelivery, 0, user)
    replacements['<mm-delivery-disable-button>'] = list.FormatOptionButton(
            mm_cfg.DisableDelivery, 1, user)
    replacements['<mm-disabled-notice>'] = list.FormatDisabledNotice(user)
    replacements['<mm-dont-ack-posts-button>'] = list.FormatOptionButton(
            mm_cfg.AcknowlegePosts, 0, user)
    replacements['<mm-ack-posts-button>'] = list.FormatOptionButton(
            mm_cfg.AcknowlegePosts, 1, user)
    replacements['<mm-receive-own-mail-button>'] = list.FormatOptionButton(
            mm_cfg.DontReceiveOwnPosts, 0, user)
    replacements['<mm-dont-receive-own-mail-button>'] = list.FormatOptionButton(
            mm_cfg.DontReceiveOwnPosts, 1, user)
    replacements['<mm-public-subscription-button>'] = list.FormatOptionButton(
            mm_cfg.ConcealSubscription, 0, user)
    replacements['<mm-hide-subscription-button>'] = list.FormatOptionButton(
            mm_cfg.ConcealSubscription, 1, user)

    replacements['<mm-digest-submit>'] = list.FormatButton('setdigest',
                                                           'Submit My Changes')
    replacements['<mm-unsubscribe-button>'] = list.FormatButton('unsub', 'Unsubscribe')
    replacements['<mm-digest-pw-box>'] = list.FormatSecureBox('digpw')
    replacements['<mm-unsub-pw-box>'] = list.FormatSecureBox('upw')
    replacements['<mm-old-pw-box>'] = list.FormatSecureBox('opw')
    replacements['<mm-new-pass-box>'] = list.FormatSecureBox('newpw')
    replacements['<mm-confirm-pass-box>'] = list.FormatSecureBox('confpw')
    replacements['<mm-change-pass-button>'] = list.FormatButton('changepw',
                                                                "Change My Password")
    replacements['<mm-form-start>'] = list.FormatFormStart('handle_opts', user)
    replacements['<mm-user>'] = user
    replacements['<mm-presentable-user>'] = presentable_user
    replacements['<mm-email-my-pw>'] = list.FormatButton('emailpw',
                                                         'Email My Password To Me')


    doc.AddItem(list.ParseTags('options.html', replacements))
    print doc.Format()
