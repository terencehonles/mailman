# Copyright (C) 2003 by the Free Software Foundation, Inc.
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

"""A MemberAdaptor based on the Berkeley database wrapper for Python.

Requires Python 2.2.2 or newer, and PyBSDDB3 4.1.3 or newer.
"""

# To use, put the following in a file called extend.py in the mailing list's
# directory:
#
# from Mailman.BDBMemberAdaptor import extend
#
# that's it!

import os
import new
import time
import errno
import struct
import cPickle as pickle

try:
    # Python 2.3
    from bsddb import db
except ImportError:
    # earlier Pythons
    from bsddb3 import db

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman import MemberAdaptor
from Mailman.MailList import MailList
from Mailman.Logging.Syslog import syslog

STORAGE_VERSION = 'BA01'
FMT = '>BHB'
FMTSIZE = struct.calcsize(FMT)

REGDELIV = 1
DIGDELIV = 2
REGFLAG = struct.pack('>B', REGDELIV)
DIGFLAG = struct.pack('>B', DIGDELIV)

# Positional arguments for _unpack()
CPADDR = 0
PASSWD = 1
LANG = 2
NAME = 3
DIGEST = 4
OPTIONS = 5
STATUS = 6



class BDBMemberAdaptor(MemberAdaptor.MemberAdaptor):
    def __init__(self, mlist):
        self._mlist = mlist
        # metainfo -- {key -> value}
        #     This table contains storage metadata information.  The keys and
        #     values are simple strings of variable length.   Here are the
        #     valid keys:
        #
        #         version - the version of the database
        #
        #  members -- {address | rec}
        #     For all regular delivery members, this maps from the member's
        #     key to their data record, which is a string concatenated of the
        #     following:
        #
        #     -- fixed data (as a packed struct)
        #        + 1-byte digest or regular delivery flag
        #        + 2-byte option flags
        #        + 1-byte delivery status
        #     -- variable data (as a pickle of a tuple)
        #        + their case preserved address or ''
        #        + their plaintext password
        #        + their chosen language
        #        + their realname or ''
        #
        # status -- {address | status+time}
        #     Maps the member's key to their delivery status and change time.
        #     These are passed as a tuple and are pickled for storage.
        #
        # topics -- {address | topicstrings}
        #     Maps the member's key to their topic strings, concatenated and
        #     separated by SEP
        #
        # bounceinfo -- {address | bounceinfo}
        #     Maps the member's key to their bounceinfo, as a pickle
        #
        # Make sure the database directory exists
        path = os.path.join(mlist.fullpath(), 'member.db')
        exists = False
        try:
            os.mkdir(path, 02775)
        except OSError, e:
            if e.errno <> errno.EEXIST: raise
            exists = True
        # Create the environment
        self._env = env = db.DBEnv()
        if exists:
            # We must join an existing environment, otherwise we'll get
            # DB_RUNRECOVERY errors when the second process to open the
            # environment begins a transaction.  I don't get it.
            env.open(path, db.DB_JOINENV)
        else:
            env.open(path,
                     db.DB_CREATE |
                     db.DB_RECOVER |
                     db.DB_INIT_MPOOL |
                     db.DB_INIT_TXN
                     )
        self._txn = None
        self._tables = []
        self._metainfo = self._setupDB('metainfo')
        self._members = self._setupDB('members')
        self._status = self._setupDB('status')
        self._topics = self._setupDB('topics')
        self._bounceinfo = self._setupDB('bounceinfo')
        # Check the database version number
        version = self._metainfo.get('version')
        if version is None:
            # Initialize
            try:
                self.txn_begin()
                self._metainfo.put('version', STORAGE_VERSION, txn=self._txn)
            except:
                self.txn_abort()
                raise
            else:
                self.txn_commit()
        else:
            # Currently there's nothing to upgrade
            assert version == STORAGE_VERSION

    def _setupDB(self, name):
        d = db.DB(self._env)
        openflags = db.DB_CREATE
        # db 4.1 requires that databases be opened in a transaction.  We'll
        # use auto commit, but only if that flag exists (i.e. we're using at
        # least db 4.1).
        try:
            openflags |= db.DB_AUTO_COMMIT
        except AttributeError:
            pass
        d.open(name, db.DB_BTREE, openflags)
        self._tables.append(d)
        return d

    def _close(self):
        self.txn_abort()
        for d in self._tables:
            d.close()
        # Checkpoint the database twice, as recommended by Sleepycat
        self._checkpoint()
        self._checkpoint()
        self._env.close()

    def _checkpoint(self):
        self._env.txn_checkpoint(0, 0, db.DB_FORCE)

    def txn_begin(self):
        assert self._txn is None
        self._txn = self._env.txn_begin()

    def txn_commit(self):
        assert self._txn is not None
        self._txn.commit()
        self._checkpoint()
        self._txn = None

    def txn_abort(self):
        if self._txn is not None:
            self._txn.abort()
            self._checkpoint()
        self._txn = None

    def _unpack(self, member):
        # Assume member is a LCE (i.e. lowercase key)
        rec = self._members.get(member.lower())
        assert rec is not None
        fixed = struct.unpack(FMT, rec[:FMTSIZE])
        vari = pickle.loads(rec[FMTSIZE:])
        return vari + fixed

    def _pack(self, member, cpaddr, passwd, lang, name, digest, flags, status):
        # Assume member is a LCE (i.e. lowercase key)
        fixed = struct.pack(FMT, digest, flags, status)
        vari = pickle.dumps((cpaddr, passwd, lang, name))
        self._members.put(member.lower(), fixed+vari, txn=self._txn)

    # MemberAdaptor writeable interface

    def addNewMember(self, member, **kws):
        assert self._mlist.Locked()
        # Make sure this address isn't already a member
        if self.isMember(member):
            raise Errors.MMAlreadyAMember, member
        # Parse the keywords
        digest = False
        password = Utils.MakeRandomPassword()
        language = self._mlist.preferred_language
        realname = None
        if kws.has_key('digest'):
            digest = kws['digest']
            del kws['digest']
        if kws.has_key('password'):
            password = kws['password']
            del kws['password']
        if kws.has_key('language'):
            language = kws['language']
            del kws['language']
        if kws.has_key('realname'):
            realname = kws['realname']
            del kws['realname']
        # Assert that no other keywords are present
        if kws:
            raise ValueError, kws.keys()
        # Should we store the case-preserved address?
        if Utils.LCDomain(member) == member.lower():
            cpaddress = ''
        else:
            cpaddress = member
        # Calculate the realname
        if realname is None:
            realname = ''
        # Calculate the digest flag
        if digest:
            digest = DIGDELIV
        else:
            digest = REGDELIV
        self._pack(member.lower(),
                   cpaddress, password, language, realname,
                   digest, self._mlist.new_member_options,
                   MemberAdaptor.ENABLED)

    def removeMember(self, member):
        txn = self._txn
        assert txn is not None
        assert self._mlist.Locked()
        self.__assertIsMember(member)
        key = member.lower()
        # Remove the table entries
        self._members.delete(key, txn=txn)
        if self._status.has_key(key):
            self._status.delete(key, txn=txn)
        if self._topics.has_key(key):
            self._topics.delete(key, txn=txn)
        if self._bounceinfo.has_key(key):
            self._bounceinfo.delete(key, txn=txn)

    def changeMemberAddress(self, member, newaddress, nodelete=0):
        assert self._mlist.Locked()
        self.__assertIsMember(member)
        okey = member.lower()
        nkey = newaddress.lower()
        txn = self._txn
        assert txn is not None
        # First, store a new member record, changing the case preserved addr.
        # Then delete the old record.
        cpaddr, passwd, lang, name, digest, flags, sts = self._unpack(okey)
        self._pack(nkey, newaddress, passwd, lang, name, digest, flags, sts)
        if not nodelete:
            self._members.delete(okey, txn)
        # Copy over the status times, topics, and bounce info, if present
        timestr = self._status.get(okey)
        if timestr is not None:
            self._status.put(nkey, timestr, txn=txn)
            if not nodelete:
                self._status.delete(okey, txn)
        topics = self._topics.get(okey)
        if topics is not None:
            self._topics.put(nkey, topics, txn=txn)
            if not nodelete:
                self._topics.delete(okey, txn)
        binfo = self._bounceinfo.get(nkey)
        if binfo is not None:
            self._binfo.put(nkey, binfo, txn=txn)
            if not nodelete:
                self._binfo.delete(okey, txn)

    def setMemberPassword(self, member, password):
        assert self._mlist.Locked()
        self.__assertIsMember(member)
        member = member.lower()
        cpaddr, oldpw, lang, name, digest, flags, status = self._unpack(member)
        self._pack(member, cpaddr, password, lang, name, digest, flags, status)

    def setMemberLanguage(self, member, language):
        assert self._mlist.Locked()
        self.__assertIsMember(member)
        member = member.lower()
        cpaddr, passwd, olang, name, digest, flags, sts = self._unpack(member)
        self._pack(member, cpaddr, passwd, language, name, digest, flags, sts)

    def setMemberOption(self, member, flag, value):
        assert self._mlist.Locked()
        self.__assertIsMember(member)
        member = member.lower()
        cpaddr, passwd, lang, name, digest, options, sts = self._unpack(member)
        # Sanity check for the digest flag
        if flag == mm_cfg.Digests:
            if value:
                # Be sure the list supports digest delivery
                if not self._mlist.digestable:
                    raise Errors.CantDigestError
                digest = DIGDELIV
            else:
                # Be sure the list supports regular delivery
                if not self._mlist.nondigestable:
                    raise Errors.MustDigestError
                # When toggling off digest delivery, we want to be sure to set
                # things up so that the user receives one last digest,
                # otherwise they may lose some email
                self._mlist.one_last_digest[member] = cpaddr
                digest = REGDELIV
        else:
            if value:
                options |= flag
            else:
                options &= ~flag
        self._pack(member, cpaddr, passwd, lang, name, digest, options, sts)

    def setMemberName(self, member, realname):
        assert self._mlist.Locked()
        self.__assertIsMember(member)
        member = member.lower()
        cpaddr, passwd, lang, oldname, digest, flags, sts = self._unpack(
            member)
        self._pack(member, cpaddr, passwd, lang, realname, digest, flags, sts)

    def setMemberTopics(self, member, topics):
        assert self._mlist.Locked()
        self.__assertIsMember(member)
        member = member.lower()
        if topics:
            self._topics.put(member, SEP.join(topics), txn=self._txn)
        elif self._topics.has_key(member):
            # No record is the same as no topics
            self._topics.delete(member, self._txn)

    def setDeliveryStatus(self, member, status):
        assert status in (MemberAdaptor.ENABLED,  MemberAdaptor.UNKNOWN,
                          MemberAdaptor.BYUSER,   MemberAdaptor.BYADMIN,
                          MemberAdaptor.BYBOUNCE)
        assert self._mlist.Locked()
        self.__assertIsMember(member)
        if status == MemberAdaptor.ENABLED:
            # Enable by resetting their bounce info
            self.setBounceInfo(member, None)
        else:
            # Pickle up the status an the current time and store that in the
            # database.  Use binary mode.
            data = pickle.dumps((status, time.time()), 1)
            self._status.put(member.lower(), data, txn=self._txn)

    def setBounceInfo(self, member, info):
        assert self._mlist.Locked()
        self.__assertIsMember(member)
        member = member.lower()
        if info is None:
            # This means to reset the bounce and delivery status information
            if self._bounceinfo.has_key(member):
                self._bounceinfo.delete(member, self._txn)
            if self._status.has_key(member):
                self._status.delete(member, self._txn)
        else:
            # Use binary mode
            data = pickle.dumps(info, 1)
            self._status.put(member, data, txn=self._txn)

    # The readable interface

    # BAW: It would be more efficient to simply return the iterator, but
    # modules like admin.py can't handle that yet.  They requires lists.
    def getMembers(self):
        return list(_AllMembersIterator(self._members))

    def getRegularMemberKeys(self):
        return list(_DeliveryMemberIterator(self._members, REGFLAG))

    def getDigestMemberKeys(self):
        return list(_DeliveryMemberIterator(self._members, DIGFLAG))

    def __assertIsMember(self, member):
        if not self.isMember(member):
            raise Errors.NotAMemberError, member

    def isMember(self, member):
        return self._members.has_key(member.lower())

    def getMemberKey(self, member):
        self.__assertIsMember(member)
        return member.lower()

    def getMemberCPAddress(self, member):
        self.__assertIsMember(member)
        cpaddr = self._unpack(member)[CPADDR]
        if cpaddr:
            return cpaddr
        return member

    def getMemberCPAddresses(self, members):
        rtn = []
        for member in members:
            member = member.lower()
            if self._members.has_key(member):
                rtn.append(self._unpack(member)[CPADDR])
            else:
                rtn.append(None)
        return rtn

    def authenticateMember(self, member, response):
        self.__assertIsMember(member)
        passwd = self._unpack(member)[PASSWD]
        if passwd == response:
            return passwd
        return False

    def getMemberPassword(self, member):
        self.__assertIsMember(member)
        return self._unpack(member)[PASSWD]

    def getMemberLanguage(self, member):
        if not self.isMember(member):
            return self._mlist.preferred_language
        lang = self._unpack(member)[LANG]
        if lang in self._mlist.GetAvailableLanguages():
            return lang
        return self._mlist.preferred_language

    def getMemberOption(self, member, flag):
        self.__assertIsMember(member)
        if flag == mm_cfg.Digests:
            return self._unpack(member)[DIGEST] == DIGDELIV
        options = self._unpack(member)[OPTIONS]
        return bool(options & flag)

    def getMemberName(self, member):
        self.__assertIsMember(member)
        name = self._unpack(member)[NAME]
        return name or None

    def getMemberTopics(self, member):
        self.__assertIsMember(member)
        topics = self._topics.get(member.lower(), '')
        if not topics:
            return []
        return topics.split(SEP)

    def getDeliveryStatus(self, member):
        self.__assertIsMember(member)
        data = self._status.get(member.lower())
        if data is None:
            return MemberAdaptor.ENABLED
        status, when = pickle.loads(data)
        return status

    def getDeliveryStatusChangeTime(self, member):
        self.__assertIsMember(member)
        data = self._status.get(member.lower())
        if data is None:
            return 0
        status, when = pickle.loads(data)
        return when

    # BAW: see above, re iterators
    def getDeliveryStatusMembers(self, status=(MemberAdaptor.UNKNOWN,
                                               MemberAdaptor.BYUSER,
                                               MemberAdaptor.BYADMIN,
                                               MemberAdaptor.BYBOUNCE)):
        return list(_StatusMemberIterator(self._members, self._status, status))

    def getBouncingMembers(self):
        return list(_BouncingMembersIterator(self._bounceinfo))

    def getBounceInfo(self, member):
        self.__assertIsMember(member)
        return self._bounceinfo.get(member.lower())



class _MemberIterator:
    def __init__(self, table):
        self._table = table
        self._c = table.cursor()

    def __iter__(self):
        raise NotImplementedError

    def next(self):
        raise NotImplementedError

    def close(self):
        if self._c:
            self._c.close()
            self._c = None

    def __del__(self):
        self.close()


class _AllMembersIterator(_MemberIterator):
    def __iter__(self):
        return _AllMembersIterator(self._table)

    def next(self):
        rec = self._c.next()
        if rec:
            return rec[0]
        self.close()
        raise StopIteration


class _DeliveryMemberIterator(_MemberIterator):
    def __init__(self, table, flag):
        _MemberIterator.__init__(self, table)
        self._flag = flag

    def __iter__(self):
        return _DeliveryMemberIterator(self._table, self._flag)

    def next(self):
        rec = self._c.next()
        while rec:
            addr, data = rec
            if data[0] == self._flag:
                return addr
            rec = self._c.next()
        self.close()
        raise StopIteration


class _StatusMemberIterator(_MemberIterator):
    def __init__(self, table, statustab, status):
        _MemberIterator.__init__(self, table)
        self._statustab = statustab
        self._status = status

    def __iter__(self):
        return _StatusMemberIterator(self._table,
                                     self._statustab,
                                     self._status)

    def next(self):
        rec = self._c.next()
        while rec:
            addr = rec[0]
            data = self._statustab.get(addr)
            if data is None:
                status = MemberAdaptor.ENABLED
            else:
                status, when = pickle.loads(data)
            if status in self._status:
                return addr
            rec = self._c.next()
        self.close()
        raise StopIteration


class _BouncingMembersIterator(_MemberIterator):
    def __iter__(self):
        return _BouncingMembersIterator(self._table)

    def next(self):
        rec = self._c.next()
        if rec:
            return rec[0]
        self.close()
        raise StopIteration



# For extend.py
def fixlock(mlist):
    def Lock(self, timeout=0):
        MailList.Lock(self, timeout)
        try:
            self._memberadaptor.txn_begin()
        except:
            MailList.Unlock(self)
            raise
    mlist.Lock = new.instancemethod(Lock, mlist, MailList)


def fixsave(mlist):
    def Save(self):
        self._memberadaptor.txn_commit()
        MailList.Save(self)
    mlist.Save = new.instancemethod(Save, mlist, MailList)


def fixunlock(mlist):
    def Unlock(self):
        # It's fine to abort the transaction even if there isn't one in
        # process, say because the Save() already committed it
        self._memberadaptor.txn_abort()
        MailList.Unlock(self)
    mlist.Unlock = new.instancemethod(Unlock, mlist, MailList)


def extend(mlist):
    mlist._memberadaptor = BDBMemberAdaptor(mlist)
    fixlock(mlist)
    fixsave(mlist)
    fixunlock(mlist)
    # To make sure we got everything, let's actually delete the
    # OldStyleMemberships dictionaries.  Assume if it has one, it has all
    # attributes.
    try:
        del mlist.members
        del mlist.digest_members
        del mlist.passwords
        del mlist.language
        del mlist.user_options
        del mlist.usernames
        del mlist.topics_userinterest
        del mlist.delivery_status
        del mlist.bounce_info
    except AttributeError:
        pass
    # BAW: How can we ensure that the BDBMemberAdaptor is closed?
