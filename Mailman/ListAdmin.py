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

"""Mixin class for MailList which handles administrative requests.

Two types of admin requests are currently supported: adding members to a
closed or semi-closed list, and moderated posts.

Pending subscriptions which are requiring a user's confirmation are handled
elsewhere.
"""

import os
import time
import marshal
import errno

from mimelib.Generator import Generator
from mimelib.Parser import Parser

from Mailman import Message
from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman.Queue.sbcache import get_switchboard
from Mailman.Logging.Syslog import syslog
from Mailman.pythonlib.StringIO import StringIO
from Mailman.i18n import _

# Request types requiring admin approval
HELDMSG = 1
SUBSCRIPTION = 2

# Return status from __handlepost()
DEFER = 0
REMOVE = 1
LOST = 2

DASH = '-'
NL = '\n'



class ListAdmin:
    def InitVars(self):
        # non-configurable data
        self.next_request_id = 1

    def InitTempVars(self):
        self.__db = None
        self.__filename = None
        fullpath = self.fullpath()
        if fullpath:
            self.__filename = os.path.join(fullpath, 'request.db')

    def __opendb(self):
        if self.__db is None:
            assert self.Locked() and self.__filename
            try:
                fp = open(self.__filename)
                self.__db = marshal.load(fp)
                fp.close()
            except IOError, e:
                if e.errno <> errno.ENOENT: raise
                self.__db = {}

    def __closedb(self):
        if self.__db is not None:
            assert self.Locked()
            omask = os.umask(002)
            try:
                fp = open(self.__filename, 'w')
                marshal.dump(self.__db, fp)
                fp.close()
                self.__db = None
            finally:
                os.umask(omask)

    def __request_id(self):
	id = self.next_request_id
	self.next_request_id += 1
	return id

    def SaveRequestsDb(self):
        self.__closedb()

    def NumRequestsPending(self):
        self.__opendb()
        return len(self.__db)

    def __getmsgids(self, rtype):
        self.__opendb()
        ids = [k for k, (type, data) in self.__db.items() if type == rtype]
        ids.sort()
        return ids

    def GetHeldMessageIds(self):
        return self.__getmsgids(HELDMSG)

    def GetSubscriptionIds(self):
        return self.__getmsgids(SUBSCRIPTION)

    def GetRecord(self, id):
        self.__opendb()
        type, data = self.__db[id]
        return data

    def GetRecordType(self, id):
        self.__opendb()
        type, data = self.__db[id]
        return type

    def HandleRequest(self, id, value, comment=None, preserve=None,
                      forward=None, addr=None):
        self.__opendb()
        rtype, data = self.__db[id]
        if rtype == HELDMSG:
            status = self.__handlepost(data, value, comment, preserve,
                                       forward, addr)
        else:
            assert rtype == SUBSCRIPTION
            status = self.__handlesubscription(data, value, comment)
        if status:
            del self.__db[id]

    def HoldMessage(self, msg, reason, msgdata={}):
        # Make a copy of msgdata so that subsequent changes won't corrupt the
        # request database.  TBD: remove the `filebase' key since this will
        # not be relevant when the message is resurrected.
        newmsgdata = {}
        newmsgdata.update(msgdata)
        msgdata = newmsgdata
        # assure that the database is open for writing
        self.__opendb()
        # get the next unique id
        id = self.__request_id()
        assert not self.__db.has_key(id)
        # get the message sender
        sender = msg.get_sender()
        # calculate the file name for the message text and write it to disk
        filename = 'heldmsg-%s-%d.txt' % (self.internal_name(), id)
        omask = os.umask(002)
        try:
            fp = open(os.path.join(mm_cfg.DATA_DIR, filename), 'w')
            g = Generator(fp)
            g.write(msg)
            fp.close()
        finally:
            os.umask(omask)
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
        self.__db[id] = (HELDMSG, data)

    def __handlepost(self, record, value, comment, preserve, forward, addr):
        # For backwards compatibility with pre 2.0beta3
        if len(record) == 5:
            ptime, sender, subject, reason, filename = record
            msgdata = {}
        else:
            # New format of record
            ptime, sender, subject, reason, filename, msgdata = record
        path = os.path.join(mm_cfg.DATA_DIR, filename)
        # Handle message preservation
        if preserve:
            parts = os.path.split(path)[1].split(DASH)
            parts[0] = 'spam'
            spamfile = DASH.join(parts)
            import shutil
            try:
                shutil.copy(path, os.path.join(mm_cfg.SPAM_DIR, spamfile))
            except IOError, e:
                if e.errno <> errno.ENOENT: raise
                return LOST
        # Now handle updates to the database
        rejection = None
        fp = None
        msg = None
        status = REMOVE
        if value == mm_cfg.DEFER:
            # Defer
            status = DEFER
        elif value == mm_cfg.APPROVE:
            # Approved
            try:
                fp = open(path)
            except IOError, e:
                if e.errno <> errno.ENOENT: raise
                return LOST
            p = Parser(Message.Message)
            msg = p.parse(fp)
            msgdata['approved'] = 1
            # Calculate a new filebase for the approved message, otherwise
            # delivery errors will cause duplicates.
            try:
                del msgdata['filebase']
            except KeyError:
                pass
            # Queue the file for delivery by qrunner.  Trying to deliver the
            # message directly here can lead to a huge delay in web
            # turnaround.
            syslog('vette', 'approved held message enqueued: %s', filename)
            # Stick the message back in the incoming queue for further
            # processing.
            inq = get_switchboard(mm_cfg.INQUEUE_DIR)
            inq.enqueue(msg, _metadata=msgdata)
        elif value == mm_cfg.REJECT:
            # Rejected
            rejection = 'Refused'
            # FIXME
            os.environ['LANG'] = pluser = self.GetPreferredLanguage(sender)
            self.__refuse(_('Posting of your message titled "%(subject)s"'),
                          sender, comment or _('[No reason given]'),
                          lang=pluser)
        else:
            assert value == mm_cfg.DISCARD
            # Discarded
            rejection = 'Discarded'
        #
        # Forward the message
        if forward and addr:
            # If we've approved the message, we need to be sure to craft a
            # completely unique second message for the forwarding operation,
            # since we don't want to share any state or information with the
            # normal delivery.
            p = Parser(Message.Message)
            if msg:
                fp.seek(0)
            else:
                try:
                    fp = open(path)
                except IOError, e:
                    if e.errno <> errno.ENOENT: raise
                    raise Errors.LostHeldMessage(path)
            msg = p.parse(fp)
            if fp:
                fp.close()
            # We don't want this message getting delivered to the list twice.
            # This should also uniquify the message enough for the hash-based
            # file naming (not foolproof though).
            del msg['resent-to']
            msg['Resent-To'] = addr
            virginq = get_switchboard(mm_cfg.VIRGINQUEUE_DIR)
            virginq.enqueue(msg, listname=self.internal_name(),
                            recips=[addr])
        #
        # Log the rejection
	if rejection:
            note = '''%(listname)s: %(rejection)s posting:
\tFrom: %(sender)s
\tSubject: %(subject)s''' % {
                'listname' : self.internal_name(),
                'rejection': rejection,
                'sender'   : sender.replace('%', '%%'),
                'subject'  : subject.replace('%', '%%'),
                }
            if comment:
                note += '\n\tReason: ' + comment.replace('%', '%%')
            syslog('vette', note)
        # Always unlink the file containing the message text.  It's not
        # necessary anymore, regardless of the disposition of the message.
        if status <> DEFER:
            try:
                os.unlink(path)
            except OSError, e:
                if e.errno <> errno.ENOENT: raise
                # We lost the message text file.  Clean up our housekeeping
                # and raise an exception.
                return LOST
        return status
            
    def HoldSubscription(self, addr, password, digest, lang):
        # assure that the database is open for writing
        self.__opendb()
        # get the next unique id
        id = self.__request_id()
        assert not self.__db.has_key(id)
        #
        # save the information to the request database. for held subscription
        # entries, each record in the database will be one of the following
        # format:
        #
        # the time the subscription request was received
        # the subscriber's address
        # the subscriber's selected password (TBD: is this safe???)
        # the digest flag
	# the user's preferred language
        #
        data = time.time(), addr, password, digest, lang
        self.__db[id] = (SUBSCRIPTION, data)
        #
        # TBD: this really shouldn't go here but I'm not sure where else is
        # appropriate.
        syslog('vette', '%s: held subscription request from %s',
               self.real_name, addr)
        # possibly notify the administrator in default list language
        if self.admin_immed_notify:
            realname = self.real_name
            subject = _(
                'New subscription request to list %(realname)s from %(addr)s')
            text = Utils.maketext(
                'subauth.txt',
                {'username'   : addr,
                 'listname'   : self.real_name,
                 'hostname'   : self.host_name,
                 'admindb_url': self.GetScriptURL('admindb', absolute=1),
                 }, mlist=self, lang=lang)
            # This message should appear to come from the <list>-owner so as
            # to avoid any useless bounce processing.
            owneraddr = self.GetOwnerEmail()
            msg = Message.UserNotification(owneraddr, owneraddr, subject, text)
            msg.send(self, **{'tomoderators': 1})

    def __handlesubscription(self, record, value, comment):
        stime, addr, password, digest, lang = record
        if value == mm_cfg.DEFER:
            return DEFER
        elif value == mm_cfg.DISCARD:
            pass
        elif value == mm_cfg.REJECT:
            # refused
            self.__refuse(_('Subscription request'), addr, comment, lang=lang)
        else:
            # subscribe
            assert value == mm_cfg.SUBSCRIBE
            try:
                self.ApprovedAddMember(addr, password, digest, lang)
            except Errors.MMAlreadyAMember:
                # User has already been subscribed, after sending the request
                pass
            # TBD: disgusting hack: ApprovedAddMember() can end up closing
            # the request database.
            self.__opendb()
        return REMOVE


    def __refuse(self, request, recip, comment, origmsg=None, lang=None):
        adminaddr = self.GetAdminEmail()
        realname = self.real_name
	if lang is None:
            lang = self.preferred_language
        text = Utils.maketext(
            'refuse.txt',
            {'listname' : realname,
             'request'  : request,
             'reason'   : comment,
             'adminaddr': adminaddr,
            }, lang=lang, mlist=self)
        # add in original message, but not wrap/filled
        if origmsg:
            text = NL.join(
                [text,
                 '---------- ' + _('Original Message') + ' ----------',
                 str(origmsg)
                 ])
        subject = _('Request to mailing list %(realname)s rejected')
        msg = Message.UserNotification(recip, adminaddr, subject, text)
        msg.send(self)
