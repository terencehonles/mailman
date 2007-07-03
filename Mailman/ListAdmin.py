# Copyright (C) 1998-2007 by the Free Software Foundation, Inc.
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

"""Mixin class for MailList which handles administrative requests.

Two types of admin requests are currently supported: adding members to a
closed or semi-closed list, and moderated posts.

Pending subscriptions which are requiring a user's confirmation are handled
elsewhere.
"""

from __future__ import with_statement

import os
import time
import email
import errno
import cPickle
import logging
import marshal

from cStringIO import StringIO
from email.Generator import Generator
from email.MIMEMessage import MIMEMessage
from email.Utils import getaddresses

from Mailman import Errors
from Mailman import Message
from Mailman import Utils
from Mailman import i18n
from Mailman.Queue.sbcache import get_switchboard
from Mailman.UserDesc import UserDesc
from Mailman.configuration import config

_ = i18n._

# Request types requiring admin approval
IGN = 0
HELDMSG = 1
SUBSCRIPTION = 2
UNSUBSCRIPTION = 3

# Return status from __handlepost()
DEFER = 0
REMOVE = 1
LOST = 2

DASH = '-'
NL = '\n'

log = logging.getLogger('mailman.vette')



class ListAdmin:
    def InitTempVars(self):
        self._db = None
        self._filename = os.path.join(self.full_path, 'request.pck')

    def _opendb(self):
        if self._db is None:
            assert self.Locked()
            try:
                with open(self._filename) as fp:
                    self._db = cPickle.load(fp)
            except IOError, e:
                if e.errno <> errno.ENOENT:
                    raise
                self._db = {}
                # put version number in new database
                self._db['version'] = IGN, config.REQUESTS_FILE_SCHEMA_VERSION

    def _closedb(self):
        if self._db is not None:
            assert self.Locked()
            # Save the version number
            self._db['version'] = IGN, config.REQUESTS_FILE_SCHEMA_VERSION
            # Now save a temp file and do the tmpfile->real file dance.  BAW:
            # should we be as paranoid as for the config.pck file?  Should we
            # use pickle?
            tmpfile = self._filename + '.tmp'
            with open(tmpfile, 'w') as fp:
                cPickle.dump(self._db, fp, 1)
                fp.flush()
                os.fsync(fp.fileno())
            self._db = None
            # Do the dance
            os.rename(tmpfile, self._filename)

    @property
    def _next_id(self):
        assert self.Locked()
        while True:
            missing = object()
            next = self.next_request_id
            self.next_request_id += 1
            if self._db.setdefault(next, missing) is missing:
                return next

    def SaveRequestsDb(self):
        self._closedb()

    def NumRequestsPending(self):
        self._opendb()
        # Subtract one for the version pseudo-entry
        return len(self._db) - 1

    def _getmsgids(self, rtype):
        self._opendb()
        ids = sorted([k for k, (op, data) in self._db.items() if op == rtype])
        return ids

    def GetHeldMessageIds(self):
        return self._getmsgids(HELDMSG)

    def GetSubscriptionIds(self):
        return self._getmsgids(SUBSCRIPTION)

    def GetUnsubscriptionIds(self):
        return self._getmsgids(UNSUBSCRIPTION)

    def GetRecord(self, id):
        self._opendb()
        type, data = self._db[id]
        return data

    def GetRecordType(self, id):
        self._opendb()
        type, data = self._db[id]
        return type

    def HandleRequest(self, id, value, comment=None, preserve=None,
                      forward=None, addr=None):
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

    def HoldMessage(self, msg, reason, msgdata={}):
        # Make a copy of msgdata so that subsequent changes won't corrupt the
        # request database.  TBD: remove the `filebase' key since this will
        # not be relevant when the message is resurrected.
        msgdata = msgdata.copy()
        # assure that the database is open for writing
        self._opendb()
        # get the next unique id
        id = self._next_id
        # get the message sender
        sender = msg.get_sender()
        # calculate the file name for the message text and write it to disk
        if config.HOLD_MESSAGES_AS_PICKLES:
            ext = 'pck'
        else:
            ext = 'txt'
        filename = 'heldmsg-%s-%d.%s' % (self.fqdn_listname, id, ext)
        with open(os.path.join(config.DATA_DIR, filename), 'w') as fp:
            if config.HOLD_MESSAGES_AS_PICKLES:
                cPickle.dump(msg, fp, 1)
            else:
                g = Generator(fp)
                g(msg, 1)
            fp.flush()
            os.fsync(fp.fileno())
        # save the information to the request database.  for held message
        # entries, each record in the database will be of the following
        # format:
        #
        # the time the message was received
        # the sender of the message
        # the message's subject
        # a string description of the problem
        # name of the file in $PREFIX/data containing the msg text
        # an additional dictionary of message metadata
        #
        msgsubject = msg.get('subject', _('(no subject)'))
        data = time.time(), sender, msgsubject, reason, filename, msgdata
        self._db[id] = (HELDMSG, data)
        return id

    def _handlepost(self, record, value, comment, preserve, forward, addr):
        # For backwards compatibility with pre 2.0beta3
        ptime, sender, subject, reason, filename, msgdata = record
        path = os.path.join(config.DATA_DIR, filename)
        # Handle message preservation
        if preserve:
            parts = os.path.split(path)[1].split(DASH)
            parts[0] = 'spam'
            spamfile = DASH.join(parts)
            # Preserve the message as plain text, not as a pickle
            try:
                with open(path) as fp:
                    msg = cPickle.load(fp)
            except IOError, e:
                if e.errno <> errno.ENOENT:
                    raise
                return LOST
            # Save the plain text to a .msg file, not a .pck file
            outpath = os.path.join(config.SPAM_DIR, spamfile)
            head, ext = os.path.splitext(outpath)
            outpath = head + '.msg'
            with open(outpath, 'w') as outfp:
                g = Generator(outfp)
                g(msg, 1)
        # Now handle updates to the database
        rejection = None
        fp = None
        msg = None
        status = REMOVE
        if value == config.DEFER:
            # Defer
            status = DEFER
        elif value == config.APPROVE:
            # Approved.
            try:
                msg = readMessage(path)
            except IOError, e:
                if e.errno <> errno.ENOENT:
                    raise
                return LOST
            msg = readMessage(path)
            msgdata['approved'] = 1
            # adminapproved is used by the Emergency handler
            msgdata['adminapproved'] = 1
            # Calculate a new filebase for the approved message, otherwise
            # delivery errors will cause duplicates.
            try:
                del msgdata['filebase']
            except KeyError:
                pass
            # Queue the file for delivery by qrunner.  Trying to deliver the
            # message directly here can lead to a huge delay in web
            # turnaround.  Log the moderation and add a header.
            msg['X-Mailman-Approved-At'] = email.Utils.formatdate(localtime=1)
            log.info('held message approved, message-id: %s',
                     msg.get('message-id', 'n/a'))
            # Stick the message back in the incoming queue for further
            # processing.
            inq = get_switchboard(config.INQUEUE_DIR)
            inq.enqueue(msg, _metadata=msgdata)
        elif value == config.REJECT:
            # Rejected
            rejection = 'Refused'
            self._refuse(_('Posting of your message titled "%(subject)s"'),
                          sender, comment or _('[No reason given]'),
                          lang=self.getMemberLanguage(sender))
        else:
            assert value == config.DISCARD
            # Discarded
            rejection = 'Discarded'
        # Forward the message
        if forward and addr:
            # If we've approved the message, we need to be sure to craft a
            # completely unique second message for the forwarding operation,
            # since we don't want to share any state or information with the
            # normal delivery.
            try:
                copy = readMessage(path)
            except IOError, e:
                if e.errno <> errno.ENOENT:
                    raise
                raise Errors.LostHeldMessage(path)
            # It's possible the addr is a comma separated list of addresses.
            addrs = getaddresses([addr])
            if len(addrs) == 1:
                realname, addr = addrs[0]
                # If the address getting the forwarded message is a member of
                # the list, we want the headers of the outer message to be
                # encoded in their language.  Otherwise it'll be the preferred
                # language of the mailing list.
                lang = self.getMemberLanguage(addr)
            else:
                # Throw away the realnames
                addr = [a for realname, a in addrs]
                # Which member language do we attempt to use?  We could use
                # the first match or the first address, but in the face of
                # ambiguity, let's just use the list's preferred language
                lang = self.preferred_language
            otrans = i18n.get_translation()
            i18n.set_language(lang)
            try:
                fmsg = Message.UserNotification(
                    addr, self.GetBouncesEmail(),
                    _('Forward of moderated message'),
                    lang=lang)
            finally:
                i18n.set_translation(otrans)
            fmsg.set_type('message/rfc822')
            fmsg.attach(copy)
            fmsg.send(self)
        # Log the rejection
        if rejection:
            note = '''%(listname)s: %(rejection)s posting:
\tFrom: %(sender)s
\tSubject: %(subject)s''' % {
                'listname' : self.internal_name(),
                'rejection': rejection,
                'sender'   : str(sender).replace('%', '%%'),
                'subject'  : str(subject).replace('%', '%%'),
                }
            if comment:
                note += '\n\tReason: ' + comment.replace('%', '%%')
            log.info('%s', note)
        # Always unlink the file containing the message text.  It's not
        # necessary anymore, regardless of the disposition of the message.
        if status <> DEFER:
            try:
                os.unlink(path)
            except OSError, e:
                if e.errno <> errno.ENOENT: raise
                # We lost the message text file.  Clean up our housekeeping
                # and inform of this status.
                return LOST
        return status

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

    def _refuse(self, request, recip, comment, origmsg=None, lang=None):
        # As this message is going to the requestor, try to set the language
        # to his/her language choice, if they are a member.  Otherwise use the
        # list's preferred language.
        realname = self.real_name
        if lang is None:
            lang = self.getMemberLanguage(recip)
        text = Utils.maketext(
            'refuse.txt',
            {'listname' : realname,
             'request'  : request,
             'reason'   : comment,
             'adminaddr': self.GetOwnerEmail(),
            }, lang=lang, mlist=self)
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
            subject = _('Request to mailing list %(realname)s rejected')
        finally:
            i18n.set_translation(otrans)
        msg = Message.UserNotification(recip, self.GetBouncesEmail(),
                                       subject, text, lang)
        msg.send(self)



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
