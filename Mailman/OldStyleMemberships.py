# Copyright (C) 2001 by the Free Software Foundation, Inc.
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

"""Old style Mailman membership adaptor.

This adaptor gets and sets member information on the MailList object given to
the constructor.  It also equates member keys and lower-cased email addresses,
i.e. KEY is LCE.

This is the adaptor used by default in Mailman 2.1.
"""

from types import StringType

from Mailman import mm_cfg
from Mailman import Utils
from Mailman import Errors
from Mailman.MemberAdaptor import MemberAdaptor

ISREGULAR = 1
ISDIGEST = 2

# XXX check for bare access to mlist.members, mlist.digest_members,
# mlist.user_options, mlist.passwords, mlist.topics_userinterest

# XXX Fix Errors.MMAlreadyAMember and Errors.NotAMember
# Actually, fix /all/ errors



class OldStyleMemberships(MemberAdaptor):
    def __init__(self, mlist):
        self.__mlist = mlist

    #
    # Read interface
    #
    def getMembers(self):
        return self.__mlist.members.keys() + self.__mlist.digest_members.keys()

    def getRegularMemberKeys(self):
        return self.__mlist.members.keys()

    def getDigestMemberKeys(self):
        return self.__mlist.digest_members.keys()

    def __get_cp_member(self, member):
        lcmember = member.lower()
        missing = []
        val = self.__mlist.members.get(lcmember, missing)
        if val is not missing:
            if isinstance(val, StringType):
                return val, ISREGULAR
            else:
                return lcmember, ISREGULAR
        val = self.__mlist.digest_members.get(lcmember, missing)
        if val is not missing:
            if isinstance(val, StringType):
                return val, ISDIGEST
            else:
                return lcmember, ISDIGEST
        return None, None

    def isMember(self, member):
        cpaddr, where = self.__get_cp_member(member)
        if cpaddr is not None:
            return 1
        return 0

    def getMemberKey(self, member):
        cpaddr, where = self.__get_cp_member(member)
        if cpaddr is None:
            raise Errors.NotAMemberError, member
        return member.lower()

    def getMemberCPAddress(self, member):
        cpaddr, where = self.__get_cp_member(member)
        if cpaddr is None:
            raise Errors.NotAMemberError, member
        return cpaddr

    def getMemberCPAddresses(self, members):
        return [self.__get_cp_member(member)[0] for member in members]

    def getMemberPassword(self, member):
        secret = self.__mlist.passwords.get(member.lower())
        if secret is None:
            raise Errors.NotAMemberError, member
        return secret

    def authenticateMember(self, member, response):
        secret = self.getMemberPassword(member)
        if secret == response:
            return secret
        return 0

    def __assertIsMember(self, member):
        if not self.isMember(member):
            raise Errors.NotAMemberError, member

    def getMemberLanguage(self, member):
        return self.__mlist.language.get(member.lower(),
                                         self.__mlist.preferred_language)

    def getMemberOption(self, member, flag):
        self.__assertIsMember(member)
        option = self.__mlist.user_options.get(member.lower(), 0)
        return not not (option & flag)

    def getMemberName(self, member):
        self.__assertIsMember(member)
        return self.__mlist.usernames.get(member.lower())

    def getMemberTopics(self, member):
        self.__assertIsMember(member)
        return self.__mlist.topics_userinterest.get(member.lower(), [])

    #
    # Write interface
    #
    def addNewMember(self, member, **kws):
        assert self.__mlist.Locked()
        # Make sure this address isn't already a member
        if self.__mlist.isMember(member):
            raise Errors.MMAlreadyAMember, member
        # Parse the keywords
        digest = 0
        password = Utils.MakeRandomPassword()
        language = self.__mlist.preferred_language
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
        # If the localpart has uppercase letters in it, then the value in the
        # members (or digest_members) dict is the case preserved address.
        # Otherwise the value is 0.  Note that the case of the domain part is
        # of course ignored.
        if Utils.LCDomain(member) == member.lower():
            value = 0
        else:
            value = member
            member = member.lower()
        if digest:
            self.__mlist.digest_members[member] = value
            # Don't use setMemberOption() here because it does too much
            self.__mlist.user_options[member] = mm_cfg.Digests
        else:
            self.__mlist.members[member] = value
        self.setMemberPassword(member, password)
        self.setMemberLanguage(member, language)
        if realname:
            self.setMemberName(member, realname)
    
    def removeMember(self, member):
        assert self.__mlist.Locked()
        self.__assertIsMember(member)
        # Delete the appropriate entries from the various MailList attributes.
        # Remember that not all of them will have an entry (only those with
        # values different than the default).
        memberkey = member.lower()
        for attr in ('passwords', 'user_options', 'members', 'digest_members',
                     'language',  'topics_userinterest',     'usernames',
                     ):
            dict = getattr(self.__mlist, attr)
            if dict.has_key(memberkey):
                del dict[memberkey]
        # A few other structures held elsewhere.  BAW: these should be
        # integrated with membership management
        self.__mlist.ClearBounceInfo(memberkey)

    def changeMemberAddress(self, member, newaddress, nodelete=0):
        assert self.__mlist.Locked()
        # Make sure the old address is a member.  Assertions that the new
        # address is not already a member is done by addNewMember() below.
        self.__assertIsMember(member)
        # Get the old values
        memberkey = member.lower()
        fullname = self.getMemberName(memberkey)
        flags = self.__mlist.user_options.get(memberkey, 0)
        digestsp = self.getMemberOption(memberkey, mm_cfg.Digests)
        password = self.__mlist.passwords.get(memberkey,
                                              Utils.MakeRandomPassword())
        lang = self.getMemberLanguage(memberkey)
        # Add the new member
        self.addNewMember(newaddress, realname=fullname, digest=digestsp,
                          password=password, language=lang)
        # Set the entire options bitfield
        if flags:
            self.__mlist.user_options[memberkey] = flags
        # Delete the old memberkey
        if not nodelete:
            self.removeMember(memberkey)

    def setMemberPassword(self, memberkey, password):
        assert self.__mlist.Locked()
        self.__assertIsMember(memberkey)
        self.__mlist.passwords[memberkey.lower()] = password

    def setMemberLanguage(self, memberkey, language):
        assert self.__mlist.Locked()
        self.__assertIsMember(memberkey)
        self.__mlist.language[memberkey.lower()] = language

    def setMemberOption(self, member, flag, value):
        assert self.__mlist.Locked()
        self.__assertIsMember(member)
        memberkey = member.lower()
        # There's one extra gotcha we have to deal with.  If the user is
        # toggling the Digests flag, then we need to move their entry from
        # mlist.members to mlist.digest_members or vice versa.  Blarg.  Do
        # this before the flag setting below in case it fails.
        if flag == mm_cfg.Digests:
            if value:
                # Be sure the list supports digest delivery
                if not self.__mlist.digestable:
                    raise Errors.CantDigestError
                # The user is turning on digest mode
                if self.__mlist.digest_members.has_key(memberkey):
                    raise Errors.AlreadyReceivingDigests, member
                cpuser = self.__mlist.members.get(memberkey)
                if cpuser is None:
                    raise Errors.NotAMemberError, member
                del self.__mlist.members[memberkey]
                self.__mlist.digest_members[memberkey] = cpuser
            else:
                # Be sure the list supports regular delivery
                if not self.__mlist.nondigestable:
                    raise Errors.MustDigestError
                # The user is turning off digest mode
                if self.__mlist.members.has_key(memberkey):
                    raise Errors.AlreadyReceivingRegularDeliveries, member
                cpuser = self.__mlist.digest_members.get(memberkey)
                if cpuser is None:
                    raise Errors.NotAMemberError, member
                del self.__mlist.digest_members[memberkey]
                self.__mlist.members[memberkey] = cpuser
                # When toggling off digest delivery, we want to be sure to set
                # things up so that the user receives one last digest,
                # otherwise they may lose some email
                self.__mlist.one_last_digest[memberkey] = cpuser
        # This is a bit kludgey because the semantics are that if the user has
        # no options set (i.e. the value would be 0), then they have no entry
        # in the user_options dict.  We use setdefault() here, and then del
        # the entry below just to make things (questionably) cleaner.
        flags = self.__mlist.user_options.setdefault(memberkey, 0)
        if value:
            self.__mlist.user_options[memberkey] |= flags
        else:
            self.__mlist.user_options[memberkey] &= ~flags
        if not self.__mlist.user_options[memberkey]:
            del self.__mlist.user_options[memberkey]

    def setMemberName(self, member, realname):
        assert self.__mlist.Locked()
        self.__assertIsMember(member)
        self.__mlist.usernames[member.lower()] = realname

    def setMemberTopics(self, member, topics):
        assert self.__mlist.Locked()
        self.__assertIsMember(member)
        memberkey = member.lower()
        if topics:
            self.__mlist.topics_userinterest[memberkey] = topics
        # if topics is empty, then delete the entry in this dictionary
        elif self.__mlist.topics_userinterest.has_key(memberkey):
            del self.__mlist.topics_userinterest[memberkey]
