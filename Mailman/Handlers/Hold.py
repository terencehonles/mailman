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

"""Determine whether this message should be held for approval.

This modules tests only for hold situations, such as messages that are too
large, messages that have potential administrivia, etc.  Definitive approvals
or denials are handled by a different module.

If no determination can be made (i.e. none of the hold criteria matches), then
we do nothing.  If the message must be held for approval, then the hold
database is updated and any administator notification messages are sent.
Finally an exception is raised to let the pipeline machinery know that further
message handling should stop.

"""

import os
import string
import time

try:
    import cPickle
    pickle = cPickle
except ImportError:
    import pickle

import HandlerAPI
from Mailman import Message
from Mailman import mm_cfg
from Mailman import Utils


class ForbiddenPoster(HandlerAPI.MessageHeld):
    "Sender is explicitly forbidden"
    pass

class ModeratedPost(HandlerAPI.MessageHeld):
    "Post to moderated list"
    pass

class NonMemberPost(HandlerAPI.MessageHeld):
    "Post by non-member to a members-only list"
    pass

class TooManyRecipients(HandlerAPI.MessageHeld):
    "Too many recipients to the message"
    pass

class ImplicitDestination(HandlerAPI.MessageHeld):
    "Message has implicit destination"
    pass

class Administrivia(HandlerAPI.MessageHeld):
    "Message may contain adbministrivia"
    pass

class SuspiciousHeaders(HandlerAPI.MessageHeld):
    "Message has a suspicious header"
    pass

class MessageTooBig(HandlerAPI.MessageHeld):
    "Message body is too big"
    pass



def process(mlist, msg):
    if getattr(msg, 'approved', 0):
        return
    # get the sender of the message
    listname = mlist.internal_name()
    adminaddr = listname + '-admin'
    sender = None
    if mm_cfg.USE_ENVELOPE_SENDER:
        sender = msg.GetEnvelopeSender()
    # Special case an ugly sendmail feature: If there exists an alias of the
    # form "owner-foo: bar" and sendmail receives mail for address "foo",
    # sendmail will change the envelope sender of the message to "bar" before
    # delivering.  This feature does not appear to be configurable.  *Boggle*.
    if not sender or sender[:len(listname)+6] == adminaddr:
        sender = msg.GetSender()
    #
    # is the poster in the list of explicitly forbidden posters?
    if len(mlist.forbidden_posters):
        forbiddens = Utils.List2Dict(mlist.forbidden_posters)
        addrs = Utils.FindMatchingAddresses(sender, forbiddens)
        if addrs:
            hold_for_approval(mlist, msg, ForbiddenPoster)
            # no return
    #
    # is the list moderated?  if so and the sender is not in the list of
    # allowed posters then hold the message.
    if mlist.moderated:
        posters = Utils.List2Dict(mlist.posters)
        addrs = Utils.FindMatchingAddresses(sender, posters)
        if not addrs:
            hold_for_approval(mlist, msg, ModeratedPost)
            # no return
    #
    # postings only from list members?  mlist.posters are allowed in addition
    # to list members
    if mlist.member_posting_only:
        posters = Utils.List2Dict(mlist.posters)
        if not mlist.IsMember(sender) and \
           not Utils.FindMatchingAddresses(sender, posters):
            # the sender is neither a member of the list, nor in the list of
            # explicitly approved posters
            hold_for_approval(mlist, msg, NonMemberPost)
            # no return
    #
    # are there too many recipients to the message?
    if mlist.max_num_recipients > 0:
        # figure out how many recipients there are
        recips = []
        toheader = msg.getheader('to')
        if toheader:
            recips = recips + map(string.strip, string.split(toheader, ','))
        ccheader = msg.getheader('cc')
        if ccheader:
            recips = recips + map(string.strip, string.split(ccheader, ','))
        if len(recips) > mlist.max_num_recipients:
            hold_for_approval(mlist, msg, TooManyRecipients)
            # no return
    #
    # implicit destination?
    if mlist.require_explicit_destination and not mlist.HasExplicitDest(msg):
        hold_for_approval(mlist, msg, ImplicitDestination)
        # no return
    #
    # possible administrivia?
    if mlist.administrivia and Utils.IsAdministrivia(msg):
        hold_for_approval(mlist, msg, Administrivia)
        # no return
    #
    # suspicious headers?
    if mlist.bounce_matching_headers:
        triggered = mlist.HasMatchingHeader(msg)
        if triggered:
            # TBD: Darn - can't include the matching line for the admin
            # message because the info would also go to the sender
            hold_for_approval(mlist, msg, SuspiciousHeaders)
            # no return
    #
    # message too big?
    if mlist.max_message_size > 0:
        if len(msg.body)/1024.0 > mlist.max_message_size:
            hold_for_approval(mlist, msg, MessageTooBig)
            # no return



def hold_for_approval(mlist, msg, excclass):
    # TBD: This should really be tied into the email confirmation system so
    # that the message can be approved or denied via email as well as the
    # Web.  That's for later though, because it would mean a revamp of the
    # MailCommandHandler too.
    #
    listname = mlist.real_name
    reason = excclass.__doc__
    sender = msg.GetSender()
    adminaddr = mlist.GetAdminEmail()
    mlist.HoldMessage(msg, reason)
    # now we need to craft and send a message to the list admin so they can
    # deal with the held message
    d = {'listname'   : listname,
         'hostname'   : mlist.host_name,
         'reason'     : reason,
         'sender'     : sender,
         'subject'    : msg.get('subject', '(no subject)'),
         'admindb_url': mlist.GetAbsoluteScriptURL('admindb'),
         }
    if mlist.admin_immed_notify:
        # get the text from the template
        subject = '%s post from %s requires approval' % (listname, sender)
        text = Utils.maketext('postauth.txt', d, raw=1)
        # craft the admin notification message and deliver it
        msg = Message.UserNotification(adminaddr, adminaddr, subject, text)
        HandlerAPI.DeliverToUser(mlist, msg)
    # We may want to send a notification to the original sender too
    fromusenet = getattr(msg, 'fromusenet', 0)
    if not fromusenet and not mlist.dont_respond_to_post_requests:
        text = Utils.maketext('postheld.txt', d)
        msg = Message.UserNotification(sender, adminaddr, subject, text)
        HandlerAPI.DeliverToUser(mlist, msg)
    # Log the held message
    mlist.LogMsg('vette', '%s post from %s held: %s' %
                 (listname, sender, reason))
    # raise the specific MessageHeld exception to exit out of the message
    # delivery pipeline
    raise excclass
