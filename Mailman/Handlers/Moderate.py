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

"""Posting moderation filter.
"""

from email.MIMEMessage import MIMEMessage
from email.MIMEText import MIMEText

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Message
from Mailman import Errors
from Mailman.i18n import _
from Mailman.Handlers import Hold



class ModeratedMemberPost(Hold.ModeratedPost):
    reason = _('Post by a moderated member')



def process(mlist, msg, msgdata):
    if msgdata.get('approved'):
        return
    # First of all, is the poster a member or not?
    sender = msg.get_sender()
    if mlist.isMember(sender):
        # If the member's moderation flag is on, then hold for approval.
        if mlist.getMemberOption(sender, mm_cfg.Moderate):
            Hold.hold_for_approval(mlist, msg, msgdata, ModeratedMemberPost)
        # Should we do anything explict to mark this message as getting past
        # this point?  No, because further pipeline handlers will need to do
        # their own thing.
        return
    # From here on out, we're dealing with non-members
    addrdict = Utils.List2Dict(mlist.accept_these_nonmembers, foldcase=1)
    if addrdict.has_key(sender):
        return
    addrdict = Utils.List2Dict(mlist.hold_these_nonmembers, foldcase=1)
    if addrdict.has_key(sender):
        Hold.hold_for_approval(mlist, msg, msgdata, Hold.ModeratedPost)
    addrdict = Utils.List2Dict(mlist.reject_these_nonmembers, foldcase=1)
    if addrdict.has_key(sender):
        do_reject(mlist)
    addrdict = Utils.List2Dict(mlist.discard_these_nonmembers, foldcase=1)
    if addrdict.has_key(sender):
        do_discard(mlist, msg)
    # Okay, so the sender wasn't specified explicitly by any of the non-member
    # moderation configuration variables.  Handle by way of generic non-member
    # action.
    assert 0 <= mlist.generic_nonmember_action <= 4
    if mlist.generic_nonmember_action == 0:
        # Accept
        return
    elif mlist.generic_nonmember_action == 1:
        Hold.hold_for_approval(mlist, msg, msgdata, Hold.ModeratedPost)
    elif mlist.generic_nonmember_action == 2:
        do_reject(mlist)
    elif mlist.generic_nonmember_action == 3:
        do_discard(mlist, msg)



def do_reject(mlist):
    listowner = mlist.GetOwnerEmail()
    raise Errors.RejectMessage, Utils.wrap(_("""\
You are not allowed to post to this mailing list, and have been automatically
rejected.  If you think that your postings are being rejected in error,
contact the mailing list owner at %(listowner)s."""))



def do_discard(mlist, msg):
    sender = msg.get_sender()
    # Do we forward auto-discards to the list owners?
    if mlist.forward_auto_discards:
        varhelp = '%s/privacy/sender/?VARHELP=discard_these_nonmembers' % \
                  mlist.GetScriptURL('admin', absolute=1)
        nmsg = Message.UserNotification(mlist.GetOwnerEmail(),
                                        mlist.GetAdminEmail(),
                                        _('Auto-discard notification'))
        nmsg['Content-Type'] = 'multipart/mixed'
        nmsg['MIME-Version'] = '1.0'
        text = MIMEText(Utils.wrap(_("""\
The attached message has been automatically discarded because the sender's
address, %(sender)s, was on the discard_these_nonmembers list.  For the list
of auto-discard addresses, see

    %(varhelp)s
""")))
        nmsg.add_payload(text)
        nmsg.add_payload(MIMEMessage(msg))
        nmsg.send(mlist)
    # Discard this sucker
    raise Errors.DiscardMessage
