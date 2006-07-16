# Copyright (C) 2006 by the Free Software Foundation, Inc.
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

"""An experimental SQLAlchemy-based membership adaptor."""

# XXX THIS FILE DOES NOT YET WORK!

import os
import re
import time

from sqlalchemy import *
from string import Template

from Mailman import Defaults
from Mailman import Errors
from Mailman import MemberAdaptor
from Mailman import Utils
from Mailman.configuration import config

NUL = '\0'



# Python classes representing the data in the SQLAlchemy database.  These will
# be associated with tables via object mappers.

class Member(object):
    def __init__(self, mlist,
                 address, realname=None, password=None,
                 digests_p=False, language=None):
        self.lckey          = address.lower()
        self.address        = address
        self.realname       = realname
        self.password       = password or Utils.MakeRandomPassword()
        self.language       = language or mlist.preferred_language
        self.digests_p      = digests_p
        self.options        = mlist.new_member_options
        self.topics         = ''
        self.status         = MemberAdaptor.ENABLED
        # XXX This should really be a datetime
        self.disable_time   = 0



_table      = None
_metadata   = None
_mapper     = None

def create_table():
    global _table, _metadata, _mapper

    if _table:
        return
    _metadata = MetaData('table metadata')
    _table = Table(
            'members', _metadata,
            Column('member_id', Integer, primary_key=True),
            Column('lckey', Unicode(), index=True, nullable=False),
            Column('address', Unicode(), index=True, nullable=False),
            Column('realname', Unicode()),
            Column('password', Unicode()),
            Column('language', String(2)),
            Column('digest', Boolean),
            Column('options', Integer),
            Column('status', Integer),
            Column('disable_time', Float),
            )
    _mapper = mapper(Member, _table)



class SAMemberships(MemberAdaptor.MemberAdaptor):
    def __init__(self, mlist):
        self._mlist     = mlist
        self._metadata  = None
        self._session   = None
        self._txn       = None

    def _connect(self):
        create_table()
        # We cannot connect in the __init__() because our adaptor requires the
        # fqdn_listname to exist.  In MailList.Create() that won't be the case.
        #
        # Calculate the engine url, expanding placeholder variables.
        engine_url = Template(config.SQLALCHEMY_ENGINE_URL).substitute(
            {'listname' : self._mlist.fqdn_listname,
             'listdir'  : os.path.join(config.LIST_DATA_DIR,
                                       self._mlist.fqdn_listname),
             })
        print 'engine_url:', engine_url
        self._engine = create_engine(engine_url)
        self._session = create_session(bind_to=self._engine)
        self._session.bind_table(_table, self._engine)
        self._session.bind_mapper(_mapper, self._engine)
        # XXX There must be a better way to figure out whether the tables need
        # to be created or not.
        try:
            _table.create()
        except exceptions.SQLError:
            pass

    #
    # The transaction interface
    #

    def load(self):
        if self._session is None:
            self._connect()
        assert self._txn is None
        self._session.clear()
        self._txn = self._session.create_transaction()

    def lock(self):
        pass

    def save(self):
        # When a MailList is first Create()'d, the load() callback doesn't get
        # called, so there will be no transaction.
        if self._txn:
            self._txn.commit()
            self._txn = None

    def unlock(self):
        if self._txn is not None:
            # The MailList has not been saved, but it is being unlocked, so
            # throw away all pending changes.
            self._txn.rollback()
            self._txn = None

    #
    # The readable interface
    #

    def getMembers(self):
        return [m.lckey for m in self._session.query(Member).select_by()]

    def getRegularMemberKeys(self):
        query = self._session.query(Member)
        return [m.lckey for m in query.select(Member.c.digests_p == False)]

    def getDigestMemberKeys(self):
        query = self._session.query(Member)
        return [m.lckey for m in query.select(Member.c.digests_p == True)]

    def _get_member(self, member):
        members = self._session.query(Member).select_by(lckey=member.lower())
        if not members:
            return None
        assert len(members) == 1
        return members[0]

    def _get_member_strict(self, member):
        member_obj = self._get_member(member)
        if not member_obj:
            raise Errors.NotAMemberError(member)
        return member_obj

    def isMember(self, member):
        return bool(self._get_member(member))

    def getMemberKey(self, member):
        self._get_member_strict(member)
        return member.lower()

    def getMemberCPAddress(self, member):
        return self._get_member(member).address

    def getMemberCPAddresses(self, members):
        query = self._session.query(Member)
        return [user.address for user in query.select(
            in_(Member.c.lckey, [m.lower() for m in members]))]

    def getMemberPassword(self, member):
        return self._get_member_strict(member).password

    def authenticateMember(self, member, response):
        return self._get_member_strict(member).password == response

    def getMemberLanguage(self, member):
        member = self._get_member(member)
        if member and member.language in self._mlist.GetAvailableLanguages():
            return member.language
        return self._mlist.preferred_language

    def getMemberOption(self, member, flag):
        return bool(self._get_member_strict(member).options & flag)

    def getMemberName(self, member):
        return self._get_member_strict(member).realname

    def getMemberTopics(self, member):
        topics = self._get_member_strict(member).topics
        if not topics:
            return []
        return topics.split(NUL)

    def getDeliveryStatus(self, member):
        return self._get_member_strict(member).status

    def getDeliveryStatusChangeTime(self, member):
        member = self._get_member_strict(member)
        if member.status == MemberAdaptor.ENABLED:
            return 0
        return member.disable_time

    def getDeliveryStatusMembers(self, status=(MemberAdaptor.UNKNOWN,
                                               MemberAdaptor.BYUSER,
                                               MemberAdaptor.BYADMIN,
                                               MemberAdaptor.BYBOUNCE)):
        query = self._session.query(Member)
        return [user.lckey for user in query.select(
            in_(Member.c.status, status))]

    def getBouncingMembers(self):
        "XXX"

    def getBounceInfo(self):
        "XXX"

    #
    # The writable interface
    #

    def addNewMember(self, member, **kws):
        assert self._mlist.Locked()
        if self.isMember(member):
            raise Errors.MMAlreadyAMember(member)
        try:
            new_member = Member(self._mlist, member, **kws)
            self._session.save(new_member)
            self._session.flush()
        except TypeError:
            # Transform exception to API specification
            raise ValueError

    def removeMember(self, memberkey):
        assert self._mlist.Locked()
        member = self._get_member_strict(memberkey)
        self._session.delete(member)

    def changeMemberAddress(self, memberkey, newaddress, nodelete=False):
        assert self._mlist.Locked()
        member = self._get_member_strict(memberkey)
        # First, add the new member from the previous data
        self.addNewMember(newaddress, member.realname, member.password,
                          member.digests_p, member.language)
        new_member = self._get_member(newaddress)
        assert new_member
        new_member.options      = member.options
        new_member.topics       = member.topics
        new_member.status       = MemberAdaptor.ENABLED
        new_member.disable_time = 0
        if not nodelete:
            self._session.delete(member)

    def setMemberPassword(self, member, password):
        assert self._mlist.Locked()
        self._get_member_strict(member).password = password

    def setMemberLanguage(self, member, language):
        assert self._mlist.Locked()
        self._get_member_strict(member).language = language

    def setMemberOption(self, member, flag, value):
        assert self._mlist.Locked()
        member = self._get_member_strict(member)
        # XXX the OldStyleMemberships adaptor will raise CantDigestError,
        # MustDigestError, AlreadyReceivingDigests, and
        # AlreadyReceivingRegularDeliveries in certain cases depending on the
        # configuration of the mailing list and the member's delivery status.
        # These semantics are not defined in the API so to keep things simple,
        # I am not reproducing them here.  Ideally, adaptors should not be
        # doing semantic integrity checks, but I'm also not going to change
        # the OldStyleMemberships adaptor.
        #
        # We still need to handle digests differently, because they aren't
        # really represented as a unique flag in the options bitfield.
        if flag == Defaults.Digests:
            member.digests_p = bool(value)
        else:
            if value:
                member.options |= flag
            else:
                member.options &= ~flag

    def setMemberName(self, member, realname):
        assert self._mlist.Locked()
        self._get_member_strict(member).realname = realname

    def setMemberTopics(self, member, topics):
        assert self._mlist.Locked()
        # For simplicity, we represent a user's topics of interest as a
        # null-joined string, which will be split properly by the accessor.
        if not topics:
            topics = None
        else:
            topics = NUL.join(topics)
        self._get_member_strict(member).topics = topics

    def setDeliveryStatus(self, member, status):
        assert status in (MemberAdaptor.ENABLED,  MemberAdaptor.UNKNOWN,
                          MemberAdaptor.BYUSER,   MemberAdaptor.BYADMIN,
                          MemberAdaptor.BYBOUNCE)
        assert self._mlist.Locked()
        member = self._get_member_strict(member)
        if status == MemberAdaptor.ENABLED:
            # XXX zap bounce info
            disable_time = 0
        else:
            disable_time = time.time()
        member.disable_time = disable_time
        member.status = status

    def setBounceInfo(self, member, info):
        "XXX"
