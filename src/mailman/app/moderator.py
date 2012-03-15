# Copyright (C) 2007-2012 by the Free Software Foundation, Inc.
#
# This file is part of GNU Mailman.
#
# GNU Mailman is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# GNU Mailman is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# GNU Mailman.  If not, see <http://www.gnu.org/licenses/>.

"""Application support for moderators."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'handle_ListDeletingEvent',
    'handle_message',
    'handle_subscription',
    'handle_unsubscription',
    'hold_message',
    'hold_subscription',
    'hold_unsubscription',
    ]


import time
import logging

from email.utils import formataddr, formatdate, getaddresses, make_msgid
from zope.component import getUtility

from mailman.app.membership import add_member, delete_member
from mailman.app.notifications import (
    send_admin_subscription_notice, send_welcome_message)
from mailman.config import config
from mailman.core.i18n import _
from mailman.email.message import UserNotification
from mailman.interfaces.action import Action
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.listmanager import ListDeletingEvent
from mailman.interfaces.member import (
    AlreadySubscribedError, DeliveryMode, NotAMemberError)
from mailman.interfaces.messages import IMessageStore
from mailman.interfaces.requests import IListRequests, RequestType
from mailman.utilities.datetime import now
from mailman.utilities.i18n import make


NL = '\n'

vlog = logging.getLogger('mailman.vette')
slog = logging.getLogger('mailman.subscribe')



def hold_message(mlist, msg, msgdata=None, reason=None):
    """Hold a message for moderator approval.

    The message is added to the mailing list's request database.

    :param mlist: The mailing list to hold the message on.
    :param msg: The message to hold.
    :param msgdata: Optional message metadata to hold.  If not given, a new
        metadata dictionary is created and held with the message.
    :param reason: Optional string reason why the message is being held.  If
        not given, the empty string is used.
    :return: An id used to handle the held message later.
    """
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
    message_id = msg.get('message-id')
    if message_id is None:
        msg['Message-ID'] = message_id = unicode(make_msgid())
    assert isinstance(message_id, unicode), (
        'Message-ID is not a unicode: %s' % message_id)
    getUtility(IMessageStore).add(msg)
    # Prepare the message metadata with some extra information needed only by
    # the moderation interface.
    msgdata['_mod_message_id'] = message_id
    msgdata['_mod_fqdn_listname'] = mlist.fqdn_listname
    msgdata['_mod_sender'] = msg.sender
    msgdata['_mod_subject'] = msg.get('subject', _('(no subject)'))
    msgdata['_mod_reason'] = reason
    msgdata['_mod_hold_date'] = now().isoformat()
    # Now hold this request.  We'll use the message_id as the key.
    requestsdb = IListRequests(mlist)
    request_id = requestsdb.hold_request(
        RequestType.held_message, message_id, msgdata)
    return request_id



def handle_message(mlist, id, action,
                   comment=None, preserve=False, forward=None):
    message_store = getUtility(IMessageStore)
    requestdb = IListRequests(mlist)
    key, msgdata = requestdb.get_request(id)
    # Handle the action.
    rejection = None
    message_id = msgdata['_mod_message_id']
    sender = msgdata['_mod_sender']
    subject = msgdata['_mod_subject']
    if action in (Action.defer, Action.hold):
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
        msg = message_store.get_message_by_id(message_id)
        # Delete moderation-specific entries from the message metadata.
        for key in msgdata.keys():
            if key.startswith('_mod_'):
                del msgdata[key]
        # Add some metadata to indicate this message has now been approved.
        msgdata['approved'] = True
        msgdata['moderator_approved'] = True
        # Calculate a new filebase for the approved message, otherwise
        # delivery errors will cause duplicates.
        if 'filebase' in msgdata:
            del msgdata['filebase']
        # Queue the file for delivery.  Trying to deliver the message directly
        # here can lead to a huge delay in web turnaround.  Log the moderation
        # and add a header.
        msg['X-Mailman-Approved-At'] = formatdate(
            time.mktime(now().timetuple()), localtime=True)
        vlog.info('held message approved, message-id: %s',
                  msg.get('message-id', 'n/a'))
        # Stick the message back in the incoming queue for further
        # processing.
        config.switchboards['pipeline'].enqueue(msg, _metadata=msgdata)
    else:
        raise AssertionError('Unexpected action: {0}'.format(action))
    # Forward the message.
    if forward:
        # Get a copy of the original message from the message store.
        msg = message_store.get_message_by_id(message_id)
        # It's possible the forwarding address list is a comma separated list
        # of display_name/address pairs.
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
        with _.using(language.code):
            fmsg = UserNotification(
                addresses, mlist.bounces_address,
                _('Forward of moderated message'),
                lang=language)
        fmsg.set_type('message/rfc822')
        fmsg.attach(msg)
        fmsg.send(mlist)
    # Delete the message from the message store if it is not being preserved.
    if not preserve:
        message_store.delete_message(message_id)
        requestdb.delete_request(id)
    # Log the rejection
    if rejection:
        note = """%s: %s posting:
\tFrom: %s
\tSubject: %s"""
        if comment:
            note += '\n\tReason: ' + comment
        vlog.info(note, mlist.fqdn_listname, rejection, sender, subject)



def hold_subscription(mlist, address, display_name, password, mode, language):
    data = dict(when=now().isoformat(),
                address=address,
                display_name=display_name,
                password=password,
                delivery_mode=str(mode),
                language=language)
    # Now hold this request.  We'll use the address as the key.
    requestsdb = IListRequests(mlist)
    request_id = requestsdb.hold_request(
        RequestType.subscription, address, data)
    vlog.info('%s: held subscription request from %s',
              mlist.fqdn_listname, address)
    # Possibly notify the administrator in default list language
    if mlist.admin_immed_notify:
        subject = _(
            'New subscription request to $mlist.display_name from $address')
        text = make('subauth.txt',
                    mailing_list=mlist,
                    username=address,
                    listname=mlist.fqdn_listname,
                    admindb_url=mlist.script_url('admindb'),
                    )
        # This message should appear to come from the <list>-owner so as
        # to avoid any useless bounce processing.
        msg = UserNotification(
            mlist.owner_address, mlist.owner_address,
            subject, text, mlist.preferred_language)
        msg.send(mlist, tomoderators=True)
    return request_id



def handle_subscription(mlist, id, action, comment=None):
    requestdb = IListRequests(mlist)
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
                lang=getUtility(ILanguageManager)[data['language']])
    elif action is Action.accept:
        key, data = requestdb.get_request(id)
        enum_value = data['delivery_mode'].split('.')[-1]
        delivery_mode = DeliveryMode(enum_value)
        address = data['address']
        display_name = data['display_name']
        language = getUtility(ILanguageManager)[data['language']]
        password = data['password']
        try:
            add_member(mlist, address, display_name, password,
                       delivery_mode, language)
        except AlreadySubscribedError:
            # The address got subscribed in some other way after the original
            # request was made and accepted.
            pass
        else:
            if mlist.send_welcome_message:
                send_welcome_message(mlist, address, language, delivery_mode)
            if mlist.admin_notify_mchanges:
                send_admin_subscription_notice(
                    mlist, address, display_name, language)
        slog.info('%s: new %s, %s %s', mlist.fqdn_listname,
                  delivery_mode, formataddr((display_name, address)),
                  'via admin approval')
    else:
        raise AssertionError('Unexpected action: {0}'.format(action))
    # Delete the request from the database.
    requestdb.delete_request(id)



def hold_unsubscription(mlist, address):
    data = dict(address=address)
    requestsdb = IListRequests(mlist)
    request_id = requestsdb.hold_request(
        RequestType.unsubscription, address, data)
    vlog.info('%s: held unsubscription request from %s',
              mlist.fqdn_listname, address)
    # Possibly notify the administrator of the hold
    if mlist.admin_immed_notify:
        subject = _(
            'New unsubscription request from $mlist.display_name by $address')
        text = make('unsubauth.txt',
                    mailing_list=mlist,
                    address=address,
                    listname=mlist.fqdn_listname,
                    admindb_url=mlist.script_url('admindb'),
                    )
        # This message should appear to come from the <list>-owner so as
        # to avoid any useless bounce processing.
        msg = UserNotification(
            mlist.owner_address, mlist.owner_address,
            subject, text, mlist.preferred_language)
        msg.send(mlist, tomoderators=True)
    return request_id



def handle_unsubscription(mlist, id, action, comment=None):
    requestdb = IListRequests(mlist)
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
        except NotAMemberError:
            # User has already been unsubscribed.
            pass
        slog.info('%s: deleted %s', mlist.fqdn_listname, address)
    else:
        raise AssertionError('Unexpected action: {0}'.format(action))
    # Delete the request from the database.
    requestdb.delete_request(id)



def _refuse(mlist, request, recip, comment, origmsg=None, lang=None):
    # As this message is going to the requester, try to set the language to
    # his/her language choice, if they are a member.  Otherwise use the list's
    # preferred language.
    display_name = mlist.display_name
    if lang is None:
        member = mlist.members.get_member(recip)
        lang = (mlist.preferred_language
                if member is None
                else member.preferred_language)
    text = make('refuse.txt',
                mailing_list=mlist,
                language=lang.code,
                listname=mlist.fqdn_listname,
                request=request,
                reason=comment,
                adminaddr=mlist.owner_address,
                )
    with _.using(lang.code):
        # add in original message, but not wrap/filled
        if origmsg:
            text = NL.join(
                [text,
                 '---------- ' + _('Original Message') + ' ----------',
                 str(origmsg)
                 ])
        subject = _('Request to mailing list "$display_name" rejected')
    msg = UserNotification(recip, mlist.bounces_address, subject, text, lang)
    msg.send(mlist)



def handle_ListDeletingEvent(event):
    if not isinstance(event, ListDeletingEvent):
        return
    # Get the held requests database for the mailing list.  Since the mailing
    # list is about to get deleted, we can delete all associated requests.
    requestsdb = IListRequests(event.mailing_list)
    for request in requestsdb.held_requests:
        requestsdb.delete_request(request.id)
