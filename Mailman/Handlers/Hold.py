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
from mimelib.MsgReader import MsgReader

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman import Message
from Mailman import i18n
from Mailman import Pending
from Mailman.Logging.Syslog import syslog

# First, play footsie with _ so that the following are marked as translated,
# but aren't actually translated until we need the text later on.
def _(s):
    return s



class ForbiddenPoster(Errors.HoldMessage):
    reason = _('Sender is explicitly forbidden')
    rejection = _('You are forbidden from posting messages to this list.')

class ModeratedPost(Errors.HoldMessage):
    reason = _('Post to moderated list')
    rejection = _('Your message was deemed inappropriate by the moderator.')

class NonMemberPost(Errors.HoldMessage):
    reason = _('Post by non-member to a members-only list')
    rejection = _('Non-members are not allowed to post messages to this list.')

class NotExplicitlyAllowed(Errors.HoldMessage):
    reason = _('Posting to a restricted list by sender requires approval')
    rejection = _('This list is restricted; your message was not approved.')

class TooManyRecipients(Errors.HoldMessage):
    reason = _('Too many recipients to the message')
    rejection = _('Please trim the recipient list; it is too long.')

class ImplicitDestination(Errors.HoldMessage):
    reason = _('Message has implicit destination')
    rejection = _('''Blind carbon copies or other implicit destinations are
not allowed.  Try reposting your message by explicitly including the list
address in the To: or Cc: fields.''')

class Administrivia(Errors.HoldMessage):
    reason = _('Message may contain administrivia')

    def rejection_notice(self, mlist):
        listurl = mlist.GetScriptURL('listinfo', absolute=1)
        request = mlist.GetRequestEmail()
        return _("""Please do *not* post administrative requests to the mailing
list.  If you wish to subscribe, visit %(listurl)s or send a message with the
word `help' in it to the request address, %(request)s, for further
instructions.""")

class SuspiciousHeaders(Errors.HoldMessage):
   reason = _('Message has a suspicious header')
   rejection = _('Your message had a suspicious header.')

class MessageTooBig(Errors.HoldMessage):
    def __init__(self, msgsize, limit):
        self.__msgsize = msgsize
        self.__limit = limit

    def reason_notice(self):
        size = self.__msgsize
        limit = self.__limit
        return _('''Message body is too big: %(size)d bytes with a limit of
%(limit)d KB''')

    def rejection_notice(self, mlist):
        kb = self.__limit
        return _('''Your message was too big; please trim it to less than
%(kb)d KB in size.''')


# And reset the translator
_ = i18n._



def process(mlist, msg, msgdata):
    if msgdata.get('approved'):
        return
    # Get the sender of the message
    listname = mlist.internal_name()
    adminaddr = listname + '-admin'
    sender = msg.get_sender()
    # Special case an ugly sendmail feature: If there exists an alias of the
    # form "owner-foo: bar" and sendmail receives mail for address "foo",
    # sendmail will change the envelope sender of the message to "bar" before
    # delivering.  This feature does not appear to be configurable.  *Boggle*.
    if not sender or sender[:len(listname)+6] == adminaddr:
        sender = msg.get_sender(use_envelope=0)
    #
    # Possible administrivia?
    if mlist.administrivia and Utils.is_administrivia(msg):
        hold_for_approval(mlist, msg, msgdata, Administrivia)
        # no return
    #
    # Is the poster in the list of explicitly forbidden posters?
    if len(mlist.forbidden_posters):
        forbiddens = Utils.List2Dict(mlist.forbidden_posters)
        addrs = Utils.FindMatchingAddresses(sender, forbiddens)
        if addrs:
            hold_for_approval(mlist, msg, msgdata, ForbiddenPoster)
            # no return
    #
    # Is the list moderated?  If so and the sender is not in the list of
    # allowed posters then hold the message.
    if mlist.moderated:
        posters = Utils.List2Dict(mlist.posters)
        addrs = Utils.FindMatchingAddresses(sender, posters)
        if not addrs:
            hold_for_approval(mlist, msg, msgdata, ModeratedPost)
            # no return
    #
    # Postings allowed only from list members?  mlist.posters are allowed in
    # addition to list members.  If not set, then only the members in posters
    # are allowed to post without approval.
    if mlist.member_posting_only:
        posters = Utils.List2Dict([s.lower() for s in mlist.posters])
        if not mlist.isMember(sender) and \
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
    # Are there too many recipients to the message?
    if mlist.max_num_recipients > 0:
        # figure out how many recipients there are
        recips = []
        toheader = msg['to']
        if toheader:
            recips.extend([s.strip() for s in toheader.split(',')])
        ccheader = msg['cc']
        if ccheader:
            recips.extend([s.strip() for s in ccheader.split(',')])
        if len(recips) > mlist.max_num_recipients:
            hold_for_approval(mlist, msg, msgdata, TooManyRecipients)
            # no return
    #
    # Implicit destination?  Note that message originating from the Usenet
    # side of the world should never be checked for implicit destination.
    if mlist.require_explicit_destination and \
           not mlist.HasExplicitDest(msg) and \
           not msgdata.get('fromusenet'):
        # then
        hold_for_approval(mlist, msg, msgdata, ImplicitDestination)
        # no return
    #
    # Suspicious headers?
    if mlist.bounce_matching_headers:
        triggered = mlist.hasMatchingHeader(msg)
        if triggered:
            # TBD: Darn - can't include the matching line for the admin
            # message because the info would also go to the sender
            hold_for_approval(mlist, msg, msgdata, SuspiciousHeaders)
            # no return
    #
    # Is the message too big?
    if mlist.max_message_size > 0:
        reader = MsgReader(msg)
        bodylen = 0
        while 1:
            line = reader.readline()
            if not line:
                break
            bodylen += len(line)
        if bodylen/1024.0 > mlist.max_message_size:
            hold_for_approval(mlist, msg, msgdata,
                              MessageTooBig(bodylen, mlist.max_message_size))
            # no return



def hold_for_approval(mlist, msg, msgdata, exc):
    # BAW: This should really be tied into the email confirmation system so
    # that the message can be approved or denied via email as well as the
    # web.  That's for later though, because it would mean a revamp of the
    # MailCommandHandler too.
    #
    if type(exc) is ClassType:
        # Go ahead and instantiate it now.
        exc = exc()
    listname = mlist.real_name
    sender = msg.get_sender()
    owneraddr = mlist.GetOwnerEmail()
    adminaddr = mlist.GetAdminEmail()
    # We need to send both the reason and the rejection notice through the
    # translator again, because of the games we play above
    reason = Utils.wrap(exc.reason_notice())
    msgdata['rejection-notice'] = Utils.wrap(exc.rejection_notice(mlist))
    id = mlist.HoldMessage(msg, reason, msgdata)
    # Now we need to craft and send a message to the list admin so they can
    # deal with the held message.
    d = {'listname'   : listname,
         'hostname'   : mlist.host_name,
         'reason'     : reason,
         'sender'     : sender,
         'subject'    : msg.get('subject', _('(no subject)')),
         'admindb_url': mlist.GetScriptURL('admindb', absolute=1),
         }
    # We may want to send a notification to the original sender too
    fromusenet = msgdata.get('fromusenet')
    # Since we're sending two messages, which may potentially be in different
    # languages (the user's preferred and the list's preferred for the admin),
    # we need to play some i18n games here.  Since the current language
    # context ought to be set up for the user, let's craft his message first.
    #
    # This message should appear to come from <list>-admin so as to handle any
    # bounce processing that might be needed.
    if not fromusenet and mlist.respond_to_post_requests:
        # Get a confirmation cookie
        cookie = Pending.new(Pending.HELD_MESSAGE, id)
        d['confirmurl'] = '%s/%s' % (mlist.GetScriptURL('confirm', absolute=1),
                                     cookie)
        lang = msgdata.get('lang', mlist.getMemberLanguage(sender))
        subject = _('Your message to %(listname)s awaits moderator approval')
        text = Utils.maketext('postheld.txt', d, lang=lang, mlist=mlist)
        msg = Message.UserNotification(sender, adminaddr, subject, text)
        msg.addheader('Content-Type', 'text/plain',
                      charset=Utils.GetCharSet(lang))
        msg.send(mlist)
    # Now the message for the list owners.  Be sure to include the list
    # moderators in this message.  This one should appear to come from
    # <list>-owner since we really don't need to do bounce processing on it.
    if mlist.admin_immed_notify:
        # Now let's temporarily set the language context to that which the
        # admin is expecting.
        otranslation = i18n.get_translation()
        i18n.set_language(mlist.preferred_language)
        try:
            # We need to regenerate or re-translate a few values in d
            usersubject = msg.get('subject', _('(no subject)'))
            d['reason'] = _(reason)
            d['subject'] = usersubject
            text = Utils.maketext('postauth.txt', d, raw=1, mlist=mlist)
            # craft the admin notification message and deliver it
            subject = _('%(listname)s post from %(sender)s requires approval')
            msg = Message.UserNotification(owneraddr, owneraddr, subject, text)
            msg.addheader('Content-Type', 'text/plain',
                          charset=Utils.GetCharSet(mlist.preferred_language))
            msg.send(mlist, **{'tomoderators': 1})
        finally:
            i18n.set_translation(otranslation)
    # Log the held message
    syslog('vette', '%s post from %s held: %s', listname, sender, reason)
    # raise the specific MessageHeld exception to exit out of the message
    # delivery pipeline
    raise exc
