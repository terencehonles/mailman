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

"""Mixin class for MailList which handles administrative requests.

Two types of admin requests are currently supported: adding members to a
closed or semi-closed list, and moderated posts.

Pending subscriptions which are requiring a user's confirmation are handled
elsewhere (currently).

"""

import os
import string
import time
import marshal
from errno import ENOENT

from Mailman import Message
from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman.pythonlib.StringIO import StringIO
from Mailman.Handlers import HandlerAPI

# Request types requiring admin approval
HELDMSG = 1
SUBSCRIPTION = 2



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
            except IOError, (code, msg):
                if code == ENOENT:
                    self.__db = {}
                else:
                    raise

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
	self.next_request_id = self.next_request_id + 1
	return id

    def SaveRequestsDb(self):
        self.__closedb()

    def NumRequestsPending(self):
        self.__opendb()
        return len(self.__db)

    def __getmsgids(self, rtype):
        self.__opendb()
        ids = []
        for k, (type, data) in self.__db.items():
            if type == rtype:
                ids.append(k)
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

    def HandleRequest(self, id, value, comment):
        self.__opendb()
        rtype, data = self.__db[id]
        del self.__db[id]
        if rtype == HELDMSG:
            self.__handlepost(data, value, comment)
        else:
            assert rtype == SUBSCRIPTION
            self.__handlesubscription(data, value, comment)

    def HoldMessage(self, msg, reason, msgdata={}):
        # assure that the database is open for writing
        self.__opendb()
        # get the next unique id
        id = self.__request_id()
        assert not self.__db.has_key(id)
        # get the message sender
        sender = msg.GetSender()
        # calculate the file name for the message text and write it to disk
        filename = 'heldmsg-%s-%d.txt' % (self.internal_name(), id)
        omask = os.umask(002)
        try:
            fp = open(os.path.join(mm_cfg.DATA_DIR, filename), 'w')
            fp.write(repr(msg))
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
        msgsubject = msg.get('subject', '(no subject)')
        data = time.time(), sender, msgsubject, reason, filename, msgdata
        self.__db[id] = (HELDMSG, data)

    def __handlepost(self, record, value, comment):
        # For backwards compatibility with pre 2.0beta3
        if len(record) == 5:
            ptime, sender, subject, reason, filename = record
            msgdata = {}
        else:
            # New format of record
            ptime, sender, subject, reason, filename, msgdata = record
        path = os.path.join(mm_cfg.DATA_DIR, filename)
        rejection = None
        if value == 0:
            # Approved
            try:
                fp = open(path)
            except IOError:
                # we lost the message text file.  clean up our housekeeping
                # and raise an exception.
                raise Errors.LostHeldMessage(path)
            msg = Message.Message(fp)
            msgdata['approved'] = 1
            # Queue the file for delivery by qrunner.  Trying to deliver the
            # message directly here can lead to a huge delay in web
            # turnaround.
            self.LogMsg('vette', 'approved held message enqueued: %s' %
                        filename)
            msg.Enqueue(self, newdata=msgdata)
        elif value == 1:
            # Rejected
            rejection = 'Refused'
            if not self.dont_respond_to_post_requests:
                self.__refuse('Posting of your message titled "%s"' % subject,
                              sender, comment or '[No reason given]')
        else:
            assert value == 2
            # Discarded
            rejection = 'Discarded'
        # Log the rejection
        def strquote(s):
            return string.replace(s, '%', '%%')

	if rejection:
            note = '''%(listname)s: %(rejection)s posting:
\tFrom: %(sender)s
\tSubject: %(subject)s''' % {
                'listname' : self.internal_name(),
                'rejection': rejection,
                'sender'   : strquote(sender),
                'subject'  : strquote(subject),
                }
            if comment:
                note = note + '\n\tReason: ' + strquote(comment)
            self.LogMsg('vette', note)
        # always unlink the file containing the message text.  It's not
        # necessary anymore, regardless of the disposition of the message.
        try:
            os.unlink(path)
        except os.error, (code, msg):
            if code == ENOENT:
                # we lost the message text file.  clean up our housekeeping
                # and raise an exception.
                raise Errors.LostHeldMessage(path)
            raise
            
    def HoldSubscription(self, addr, password, digest):
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
        #
        data = time.time(), addr, password, digest
        self.__db[id] = (SUBSCRIPTION, data)
        #
        # TBD: this really shouldn't go here but I'm not sure where else is
        # appropriate.
        self.LogMsg('vette', '%s: held subscription request from %s' %
                    (self.real_name, addr))
        # possibly notify the administrator
        if self.admin_immed_notify:
            subject = 'New subscription request to list %s from %s' % (
                self.real_name, addr)
            text = Utils.maketext(
                'subauth.txt',
                {'username'   : addr,
                 'listname'   : self.real_name,
                 'hostname'   : self.host_name,
                 'admindb_url': self.GetAbsoluteScriptURL('admindb'),
                 })
            adminaddr = self.GetAdminEmail()
            msg = Message.UserNotification(adminaddr, adminaddr, subject, text)
            HandlerAPI.DeliverToUser(self, msg)


    def __handlesubscription(self, record, value, comment):
        stime, addr, password, digest = record
        if value == 0:
            # refused
            self.__refuse('Subscription request', addr, comment)
        else:
            # subscribe
            assert value == 1
            self.ApprovedAddMember(addr, password, digest)


    def __refuse(self, request, recip, comment, origmsg=None):
        adminaddr = self.GetAdminEmail()
        text = Utils.maketext(
            'refuse.txt',
            {'listname' : self.real_name,
             'request'  : request,
             'reason'   : comment,
             'adminaddr': adminaddr,
             })
        # add in original message, but not wrap/filled
        if origmsg:
            text = string.join([text,
                                '---------- Original Message ----------',
                                str(origmsg)], '\n')
        subject = 'Request to mailing list %s rejected' % self.real_name
        msg = Message.UserNotification(recip, adminaddr, subject, text)
        HandlerAPI.DeliverToUser(self, msg)
