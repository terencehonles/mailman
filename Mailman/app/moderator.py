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
    'handle_message',
    'handle_subscription',
    'handle_unsubscription',
    'hold_message',
    'hold_subscription',
    'hold_unsubscription',
    ]

import logging

from datetime import datetime
from email.utils import formataddr, formatdate, getaddresses, make_msgid

from Mailman import Errors
from Mailman import Message
from Mailman import Utils
from Mailman import i18n
from Mailman.app.membership import add_member, delete_member
from Mailman.configuration import config
from Mailman.constants import Action, DeliveryMode
from Mailman.interfaces import RequestType
from Mailman.queue import Switchboard

_ = i18n._
__i18n_templates__ = True

vlog = logging.getLogger('mailman.vette')
slog = logging.getLogger('mailman.subscribe')



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
    sender = msgdata['_mod_sender']
    subject = msgdata['_mod_subject']
    if action is Action.defer:
        # Nothing to do, but preserve the message for later.
        preserve = True
    elif action is Action.discard:
        rejection = 'Discarded'
    elif action is Action.reject:
        rejection = 'Refused'
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
        vlog.info('held message approved, message-id: %s',
                  msg.get('message-id', 'n/a'))
        # Stick the message back in the incoming queue for further
        # processing.
        inq = Switchboard(config.INQUEUE_DIR)
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
        with i18n.using_language(language):
            fmsg = Message.UserNotification(
                addresses, mlist.bounces_address,
                _('Forward of moderated message'),
                lang=language)
        fmsg.set_type('message/rfc822')
        fmsg.attach(msg)
        fmsg.send(mlist)
    # Delete the message from the message store if it is not being preserved.
    if not preserve:
        config.db.message_store.delete_message(global_id)
        requestdb.delete_request(id)
    # Log the rejection
    if rejection:
        note = """%s: %s posting:
\tFrom: %s
\tSubject: %s"""
        if comment:
            note += '\n\tReason: ' + comment
        vlog.info(note, mlist.fqdn_listname, rejection, sender, subject)



def hold_subscription(mlist, address, realname, password, mode, language):
    data = dict(when=datetime.now().isoformat(),
                address=address,
                realname=realname,
                password=password,
                delivery_mode=str(mode),
                language=language)
    # Now hold this request.  We'll use the address as the key.
    requestsdb = config.db.requests.get_list_requests(mlist)
    request_id = requestsdb.hold_request(
        RequestType.subscription, address, data)
    vlog.info('%s: held subscription request from %s',
              mlist.fqdn_listname, address)
    # Possibly notify the administrator in default list language
    if mlist.admin_immed_notify:
        subject = _(
            'New subscription request to list $mlist.real_name from $address')
        text = Utils.maketext(
            'subauth.txt',
            {'username'   : address,
             'listname'   : mlist.fqdn_listname,
             'admindb_url': mlist.script_url('admindb'),
             }, mlist=mlist)
        # This message should appear to come from the <list>-owner so as
        # to avoid any useless bounce processing.
        msg = Message.UserNotification(
            mlist.owner_address, mlist.owner_address,
            subject, text, mlist.preferred_language)
        msg.send(mlist, tomoderators=True)
    return request_id



def handle_subscription(mlist, id, action, comment=None):
    requestdb = config.db.requests.get_list_requests(mlist)
    if action is Action.defer:
        # Nothing to do.
        return
    elif action is Action.discard:
        # Nothing to do except delete the request from the database.
        pass
    elif action is Action.reject:
        key, data = requestdb.get_request(id)
        _refuse(mlist, _('Subscription request'),
                data['address'],
                comment or _('[No reason given]'),
                lang=data['language'])
    elif action is Action.accept:
        key, data = requestdb.get_request(id)
        enum_value = data['delivery_mode'].split('.')[-1]
        delivery_mode = DeliveryMode(enum_value)
        address = data['address']
        realname = data['realname']
        try:
            add_member(mlist, address, realname, data['password'],
                       delivery_mode, data['language'])
        except Errors.AlreadySubscribedError:
            # The address got subscribed in some other way after the original
            # request was made and accepted.
            pass
        slog.info('%s: new %s, %s %s', mlist.fqdn_listname,
                  delivery_mode, formataddr((realname, address)),
                  'via admin approval')
    else:
        raise AssertionError('Unexpected action: %s' % action)
    # Delete the request from the database.
    requestdb.delete_request(id)



def hold_unsubscription(mlist, address):
    data = dict(address=address)
    requestsdb = config.db.requests.get_list_requests(mlist)
    request_id = requestsdb.hold_request(
        RequestType.unsubscription, address, data)
    vlog.info('%s: held unsubscription request from %s',
              mlist.fqdn_listname, address)
    # Possibly notify the administrator of the hold
    if mlist.admin_immed_notify:
        subject = _(
            'New unsubscription request from $mlist.real_name by $address')
        text = Utils.maketext(
            'unsubauth.txt',
            {'address'   : address,
             'listname'   : mlist.fqdn_listname,
             'admindb_url': mlist.script_url('admindb'),
             }, mlist=mlist)
        # This message should appear to come from the <list>-owner so as
        # to avoid any useless bounce processing.
        msg = Message.UserNotification(
            mlist.owner_address, mlist.owner_address,
            subject, text, mlist.preferred_language)
        msg.send(mlist, tomoderators=True)
    return request_id



def handle_unsubscription(mlist, id, action, comment=None):
    requestdb = config.db.requests.get_list_requests(mlist)
    key, data = requestdb.get_request(id)
    address = data['address']
    if action is Action.defer:
        # Nothing to do.
        return
    elif action is Action.discard:
        # Nothing to do except delete the request from the database.
        pass
    elif action is Action.reject:
        key, data = requestdb.get_request(id)
        _refuse(mlist, _('Unsubscription request'), address,
                comment or _('[No reason given]'))
    elif action is Action.accept:
        key, data = requestdb.get_request(id)
        try:
            delete_member(mlist, address)
        except Errors.NotAMemberError:
            # User has already been unsubscribed.
            pass
        slog.info('%s: deleted %s', mlist.fqdn_listname, address)
    else:
        raise AssertionError('Unexpected action: %s' % action)
    # Delete the request from the database.
    requestdb.delete_request(id)



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
    with i18n.using_language(lang):
        # add in original message, but not wrap/filled
        if origmsg:
            text = NL.join(
                [text,
                 '---------- ' + _('Original Message') + ' ----------',
                 str(origmsg)
                 ])
        subject = _('Request to mailing list "$realname" rejected')
    msg = Message.UserNotification(recip, mlist.bounces_address,
                                   subject, text, lang)
    msg.send(mlist)
