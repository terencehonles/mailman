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
import time
from types import ClassType

try:
    import cPickle
    pickle = cPickle
except ImportError:
    import pickle

import HandlerAPI
from Mailman import Message
from Mailman import mm_cfg
from Mailman import Utils
from Mailman.i18n import _
from Mailman.Logging.Syslog import syslog



class ForbiddenPoster(HandlerAPI.MessageHeld):
    "Sender is explicitly forbidden"
    rejection = 'You are forbidden from posting messages to this list.'

class ModeratedPost(HandlerAPI.MessageHeld):
    "Post to moderated list"
    rejection = 'Your message has been deemed inappropriate by the moderator.'

class NonMemberPost(HandlerAPI.MessageHeld):
    "Post by non-member to a members-only list"
    rejection = 'Non-members are not allowed to post messages to this list.'

class NotExplicitlyAllowed(HandlerAPI.MessageHeld):
    "Posting to a restricted list by sender requires approval"
    rejection = 'This list is restricted; your message was not approved.'

class TooManyRecipients(HandlerAPI.MessageHeld):
    "Too many recipients to the message"
    rejection = 'Please trim the recipient list; it is too long.'

class ImplicitDestination(HandlerAPI.MessageHeld):
    "Message has implicit destination"
    rejection = '''Blind carbon copies or other implicit destinations are
not allowed.  Try reposting your message by explicitly including the list
address in the To: or Cc: fields.'''

class Administrivia(HandlerAPI.MessageHeld):
    "Message may contain administrivia"

    def rejection_notice(self, mlist):
        return """Please do *not* post administrative requests to the mailing
list.  If you wish to subscribe, visit %(listurl)s or send a message with the
word `help' in it to the request address, %(request)s, for further
instructions.""" % {'listurl': mlist.GetScriptURL('listinfo', absolute=1),
                    'request': mlist.GetRequestEmail(),
                    }

class SuspiciousHeaders(HandlerAPI.MessageHeld):
    "Message has a suspicious header"
    rejection = 'Your message had a suspicious header.'

class MessageTooBig(HandlerAPI.MessageHeld):
    "Message body is too big: %d bytes but there's a limit of %d KB"
    def __init__(self, msgsize, limit):
        self.__msgsize = msgsize
        self.__limit = limit

    def __str__(self):
        return HandlerAPI.MessageHeld.__str__(self) % (
            self.__msgsize, self.__limit)

    def rejection_notice(self, mlist):
        return """Your message was too big; please trim it to less than
%(kb)s KB in size.""" % {'kb': mlist.max_message_size}



def process(mlist, msg, msgdata):
    if msgdata.get('approved'):
        return
    # get the sender of the message
    listname = mlist.internal_name()
    adminaddr = listname + '-admin'
    sender = msg.GetSender()
    # Special case an ugly sendmail feature: If there exists an alias of the
    # form "owner-foo: bar" and sendmail receives mail for address "foo",
    # sendmail will change the envelope sender of the message to "bar" before
    # delivering.  This feature does not appear to be configurable.  *Boggle*.
    if not sender or sender[:len(listname)+6] == adminaddr:
        sender = msg.GetSender(use_envelope=0)
    #
    # is the poster in the list of explicitly forbidden posters?
    if len(mlist.forbidden_posters):
        forbiddens = Utils.List2Dict(mlist.forbidden_posters)
        addrs = Utils.FindMatchingAddresses(sender, forbiddens)
        if addrs:
            hold_for_approval(mlist, msg, msgdata, ForbiddenPoster)
            # no return
    #
    # is the list moderated?  if so and the sender is not in the list of
    # allowed posters then hold the message.
    if mlist.moderated:
        posters = Utils.List2Dict(mlist.posters)
        addrs = Utils.FindMatchingAddresses(sender, posters)
        if not addrs:
            hold_for_approval(mlist, msg, msgdata, ModeratedPost)
            # no return
    #
    # postings only from list members?  mlist.posters are allowed in addition
    # to list members.  If not set, then only the members in posters are
    # allowed to post without approval.
    if mlist.member_posting_only:
        posters = Utils.List2Dict([s.lower() for s in mlist.posters])
        if not mlist.IsMember(sender) and \
           not Utils.FindMatchingAddresses(sender, posters):
            # the sender is neither a member of the list, nor in the list of
            # explicitly approved posters
            hold_for_approval(mlist, msg, msgdata, NonMemberPost)
            # no return
    elif mlist.posters:
        posters = Utils.List2Dict([s.lower() for s in mlist.posters])
        if not Utils.FindMatchingAddresses(sender, posters):
            # the sender is not explicitly in the list of allowed posters
            # (which is non-empty), so hold the message
            hold_for_approval(mlist, msg, msgdata, NotExplicitlyAllowed)
            # no return
    #
    # are there too many recipients to the message?
    if mlist.max_num_recipients > 0:
        # figure out how many recipients there are
        recips = []
        toheader = msg.getheader('to')
        if toheader:
            recips.extend([s.strip() for s in toheader.split(',')])
        ccheader = msg.getheader('cc')
        if ccheader:
            recips.extend([s.strip() for s in ccheader.split(',')])
        if len(recips) > mlist.max_num_recipients:
            hold_for_approval(mlist, msg, msgdata, TooManyRecipients)
            # no return
    #
    # implicit destination?  Note that message originating from the Usenet
    # side of the world should never be implicitly destined
    if mlist.require_explicit_destination and \
       not mlist.HasExplicitDest(msg) and \
       not msgdata.get('fromusenet'):
        # then
        hold_for_approval(mlist, msg, msgdata, ImplicitDestination)
        # no return
    #
    # possible administrivia?
    if mlist.administrivia and Utils.IsAdministrivia(msg):
        hold_for_approval(mlist, msg, msgdata, Administrivia)
        # no return
    #
    # suspicious headers?
    if mlist.bounce_matching_headers:
        triggered = mlist.HasMatchingHeader(msg)
        if triggered:
            # TBD: Darn - can't include the matching line for the admin
            # message because the info would also go to the sender
            hold_for_approval(mlist, msg, msgdata, SuspiciousHeaders)
            # no return
    #
    # message too big?
    if mlist.max_message_size > 0:
        bodylen = len(msg.body)
        if bodylen/1024.0 > mlist.max_message_size:
            hold_for_approval(mlist, msg, msgdata,
                              MessageTooBig(bodylen, mlist.max_message_size))
            # no return



def hold_for_approval(mlist, msg, msgdata, exc):
    # TBD: This should really be tied into the email confirmation system so
    # that the message can be approved or denied via email as well as the
    # Web.  That's for later though, because it would mean a revamp of the
    # MailCommandHandler too.
    #
    if type(exc) is ClassType:
        # Go ahead and instantiate it now.
        exc = exc()
    listname = mlist.real_name
    reason = str(exc)
    sender = msg.GetSender()
    adminaddr = mlist.GetAdminEmail()
    msgdata['rejection-notice'] = exc.rejection_notice(mlist)
    mlist.HoldMessage(msg, reason, msgdata)
    # now we need to craft and send a message to the list admin so they can
    # deal with the held message
    d = {'listname'   : listname,
         'hostname'   : mlist.host_name,
         'reason'     : reason,
         'sender'     : sender,
         'subject'    : msg.get('subject', '(no subject)'),
         'admindb_url': mlist.GetScriptURL('admindb', absolute=1),
         }
    if mlist.admin_immed_notify:
        # get the text from the template
        subject = _('%(listname)s post from %(sender)s requires approval')
        text = Utils.maketext('postauth.txt', d, raw=1)
        # craft the admin notification message and deliver it
        msg = Message.UserNotification(adminaddr, adminaddr, subject, text)
        HandlerAPI.DeliverToUser(mlist, msg)
    # We may want to send a notification to the original sender too
    fromusenet = msgdata.get('fromusenet')
    if not fromusenet and not mlist.dont_respond_to_post_requests:
        subject = _('Your message to %(listname)s awaits moderator approval')
        text = Utils.maketext('postheld.txt', d)
        msg = Message.UserNotification(sender, adminaddr, subject, text)
        HandlerAPI.DeliverToUser(mlist, msg)
    # Log the held message
    syslog('vette', '%s post from %s held: %s' % (listname, sender, reason))
    # raise the specific MessageHeld exception to exit out of the message
    # delivery pipeline
    raise exc
