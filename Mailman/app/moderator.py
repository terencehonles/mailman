# Copyright (C) 2007 by the Free Software Foundation, Inc.
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
# USA.

"""Application support for moderators."""

from __future__ import with_statement

__all__ = [
    'hold_message',
    ]

import logging

from datetime import datetime
from email.utils import formatdate, getaddresses, make_msgid

from Mailman import Message
from Mailman import Utils
from Mailman import i18n
from Mailman.Queue.sbcache import get_switchboard
from Mailman.configuration import config
from Mailman.constants import Action
from Mailman.interfaces import RequestType

_ = i18n._
__i18n_templates__ = True

log = logging.getLogger('mailman.vette')



def hold_message(mlist, msg, msgdata=None, reason=None):
    if msgdata is None:
        msgdata = {}
    else:
        # Make a copy of msgdata so that subsequent changes won't corrupt the
        # request database.  TBD: remove the `filebase' key since this will
        # not be relevant when the message is resurrected.
        msgdata = msgdata.copy()
    if reason is None:
        reason = ''
    # Add the message to the message store.  It is required to have a
    # Message-ID header.
    if 'message-id' not in msg:
        msg['Message-ID'] = make_msgid()
    seqno = config.db.message_store.add(msg)
    global_id = '%s/%s' % (msg['X-List-ID-Hash'], seqno)
    # Prepare the message metadata with some extra information needed only by
    # the moderation interface.
    msgdata['_mod_global_id'] = global_id
    msgdata['_mod_fqdn_listname'] = mlist.fqdn_listname
    msgdata['_mod_sender'] = msg.get_sender()
    msgdata['_mod_subject'] = msg.get('subject', _('(no subject)'))
    msgdata['_mod_reason'] = reason
    msgdata['_mod_hold_date'] = datetime.now().isoformat()
    # Now hold this request.  We'll use the message's global ID as the key.
    requestsdb = config.db.requests.get_list_requests(mlist)
    request_id = requestsdb.hold_request(
        RequestType.held_message, global_id, msgdata)
    return request_id



def handle_message(mlist, id, action,
                   comment=None, preserve=False, forward=None):
    requestdb = config.db.requests.get_list_requests(mlist)
    key, msgdata = requestdb.get_request(id)
    # Handle the action.
    rejection = None
    global_id = msgdata['_mod_global_id']
    if action is Action.defer:
        # Nothing to do, but preserve the message for later.
        preserve = True
    elif action is Action.discard:
        rejection = 'Discarded'
    elif action is Action.reject:
        rejection = 'Refused'
        sender = msgdata['_mod_sender']
        subject = msgdata['_mod_subject']
        member = mlist.members.get_member(sender)
        if member:
            language = member.preferred_language
        else:
            language = None
        _refuse(mlist, _('Posting of your message titled "$subject"'),
                sender, comment or _('[No reason given]'), language)
    elif action is Action.accept:
        # Start by getting the message from the message store.
        msg = config.db.message_store.get_message(global_id)
        # Delete moderation-specific entries from the message metadata.
        for key in msgdata.keys():
            if key.startswith('_mod_'):
                del msgdata[key]
        # Add some metadata to indicate this message has now been approved.
        # XXX 'adminapproved' is used for backward compatibility, but it
        # should really be called 'moderator_approved'.
        msgdata['approved'] = True
        msgdata['adminapproved'] = True
        # Calculate a new filebase for the approved message, otherwise
        # delivery errors will cause duplicates.
        if 'filebase' in msgdata:
            del msgdata['filebase']
        # Queue the file for delivery by qrunner.  Trying to deliver the
        # message directly here can lead to a huge delay in web turnaround.
        # Log the moderation and add a header.
        msg['X-Mailman-Approved-At'] = formatdate(localtime=True)
        log.info('held message approved, message-id: %s',
                 msg.get('message-id', 'n/a'))
        # Stick the message back in the incoming queue for further
        # processing.
        inq = get_switchboard(config.INQUEUE_DIR)
        inq.enqueue(msg, _metadata=msgdata)
    else:
        raise AssertionError('Unexpected action: %s' % action)
    # Forward the message.
    if forward:
        # Get a copy of the original message from the message store.
        msg = config.db.message_store.get_message(global_id)
        # It's possible the forwarding address list is a comma separated list
        # of realname/address pairs.
        addresses = [addr[1] for addr in getaddresses(forward)]
        language = mlist.preferred_language
        if len(addresses) == 1:
            # If the address getting the forwarded message is a member of
            # the list, we want the headers of the outer message to be
            # encoded in their language.  Otherwise it'll be the preferred
            # language of the mailing list.  This is better than sending a
            # separate message per recipient.
            member = mlist.members.get_member(addresses[0])
            if member:
                language = member.preferred_language
        otrans = i18n.get_translation()
        i18n.set_language(language)
        try:
            fmsg = Message.UserNotification(
                addr, mlist.bounces_address,
                _('Forward of moderated message'),
                lang=language)
        finally:
            i18n.set_translation(otrans)
        fmsg.set_type('message/rfc822')
        fmsg.attach(msg)
        fmsg.send(mlist)
    # Delete the message from the message store if it is not being preserved.
    if not preserve:
        config.db.message_store.delete_message(global_id)
        requestdb.delete_request(id)
    # Log the rejection
    if rejection:
        note = """$listname: $rejection posting:
\tFrom: $sender
\tSubject: $subject"""
        if comment:
            note += '\n\tReason: ' + comment
        log.info(note)


def HoldSubscription(self, addr, fullname, password, digest, lang):
    # Assure that the database is open for writing
    self._opendb()
    # Get the next unique id
    id = self._next_id
    # Save the information to the request database. for held subscription
    # entries, each record in the database will be one of the following
    # format:
    #
    # the time the subscription request was received
    # the subscriber's address
    # the subscriber's selected password (TBD: is this safe???)
    # the digest flag
    # the user's preferred language
    data = time.time(), addr, fullname, password, digest, lang
    self._db[id] = (SUBSCRIPTION, data)
    #
    # TBD: this really shouldn't go here but I'm not sure where else is
    # appropriate.
    log.info('%s: held subscription request from %s',
             self.internal_name(), addr)
    # Possibly notify the administrator in default list language
    if self.admin_immed_notify:
        realname = self.real_name
        subject = _(
            'New subscription request to list %(realname)s from %(addr)s')
        text = Utils.maketext(
            'subauth.txt',
            {'username'   : addr,
             'listname'   : self.internal_name(),
             'hostname'   : self.host_name,
             'admindb_url': self.GetScriptURL('admindb', absolute=1),
             }, mlist=self)
        # This message should appear to come from the <list>-owner so as
        # to avoid any useless bounce processing.
        owneraddr = self.GetOwnerEmail()
        msg = Message.UserNotification(owneraddr, owneraddr, subject, text,
                                       self.preferred_language)
        msg.send(self, **{'tomoderators': 1})

def __handlesubscription(self, record, value, comment):
    stime, addr, fullname, password, digest, lang = record
    if value == config.DEFER:
        return DEFER
    elif value == config.DISCARD:
        pass
    elif value == config.REJECT:
        self._refuse(_('Subscription request'), addr,
                      comment or _('[No reason given]'),
                      lang=lang)
    else:
        # subscribe
        assert value == config.SUBSCRIBE
        try:
            userdesc = UserDesc(addr, fullname, password, digest, lang)
            self.ApprovedAddMember(userdesc, whence='via admin approval')
        except Errors.MMAlreadyAMember:
            # User has already been subscribed, after sending the request
            pass
        # TBD: disgusting hack: ApprovedAddMember() can end up closing
        # the request database.
        self._opendb()
    return REMOVE

def HoldUnsubscription(self, addr):
    # Assure the database is open for writing
    self._opendb()
    # Get the next unique id
    id = self._next_id
    # All we need to do is save the unsubscribing address
    self._db[id] = (UNSUBSCRIPTION, addr)
    log.info('%s: held unsubscription request from %s',
             self.internal_name(), addr)
    # Possibly notify the administrator of the hold
    if self.admin_immed_notify:
        realname = self.real_name
        subject = _(
            'New unsubscription request from %(realname)s by %(addr)s')
        text = Utils.maketext(
            'unsubauth.txt',
            {'username'   : addr,
             'listname'   : self.internal_name(),
             'hostname'   : self.host_name,
             'admindb_url': self.GetScriptURL('admindb', absolute=1),
             }, mlist=self)
        # This message should appear to come from the <list>-owner so as
        # to avoid any useless bounce processing.
        owneraddr = self.GetOwnerEmail()
        msg = Message.UserNotification(owneraddr, owneraddr, subject, text,
                                       self.preferred_language)
        msg.send(self, **{'tomoderators': 1})

def _handleunsubscription(self, record, value, comment):
    addr = record
    if value == config.DEFER:
        return DEFER
    elif value == config.DISCARD:
        pass
    elif value == config.REJECT:
        self._refuse(_('Unsubscription request'), addr, comment)
    else:
        assert value == config.UNSUBSCRIBE
        try:
            self.ApprovedDeleteMember(addr)
        except Errors.NotAMemberError:
            # User has already been unsubscribed
            pass
    return REMOVE



def _refuse(mlist, request, recip, comment, origmsg=None, lang=None):
    # As this message is going to the requester, try to set the language to
    # his/her language choice, if they are a member.  Otherwise use the list's
    # preferred language.
    realname = mlist.real_name
    if lang is None:
        member = mlist.members.get_member(recip)
        if member:
            lang = member.preferred_language
    text = Utils.maketext(
        'refuse.txt',
        {'listname' : mlist.fqdn_listname,
         'request'  : request,
         'reason'   : comment,
         'adminaddr': mlist.owner_address,
        }, lang=lang, mlist=mlist)
    otrans = i18n.get_translation()
    i18n.set_language(lang)
    try:
        # add in original message, but not wrap/filled
        if origmsg:
            text = NL.join(
                [text,
                 '---------- ' + _('Original Message') + ' ----------',
                 str(origmsg)
                 ])
        subject = _('Request to mailing list "$realname" rejected')
    finally:
        i18n.set_translation(otrans)
    msg = Message.UserNotification(recip, mlist.bounces_address,
                                   subject, text, lang)
    msg.send(mlist)



def readMessage(path):
    # For backwards compatibility, we must be able to read either a flat text
    # file or a pickle.
    ext = os.path.splitext(path)[1]
    with open(path) as fp:
        if ext == '.txt':
            msg = email.message_from_file(fp, Message.Message)
        else:
            assert ext == '.pck'
            msg = cPickle.load(fp)
    return msg



def handle_request(mlist, id, value,
                   comment=None, preserve=None, forward=None, addr=None):
    requestsdb = config.db.get_list_requests(mlist)
    key, data = requestsdb.get_record(id)

    self._opendb()
    rtype, data = self._db[id]
    if rtype == HELDMSG:
        status = self._handlepost(data, value, comment, preserve,
                                  forward, addr)
    elif rtype == UNSUBSCRIPTION:
        status = self._handleunsubscription(data, value, comment)
    else:
        assert rtype == SUBSCRIPTION
        status = self._handlesubscription(data, value, comment)
    if status <> DEFER:
        # BAW: Held message ids are linked to Pending cookies, allowing
        # the user to cancel their post before the moderator has approved
        # it.  We should probably remove the cookie associated with this
        # id, but we have no way currently of correlating them. :(
        del self._db[id]
