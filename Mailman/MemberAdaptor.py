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

"""This is an interface to list-specific membership information.

This class should not be instantiated directly, but instead, it should be
subclassed for specific adaptation to membership databases.  The default
MM2.0.x style adaptor is in OldStyleMemberships.py.  Through the extend.py
mechanism, you can instantiate different membership information adaptors to
get info out of LDAP, Zope, other, or any combination of the above.

Members have three pieces of identifying information: a unique identifying
opaque key (KEY), a lower-cased email address (LCE), and a case-preserved
email (CPE) address.  Adpators must ensure that both member keys and lces can
uniquely identify a member, and that they can (usually) convert freely between
keys and lces.  Most methods must accept either a key or an lce, unless
specifically documented otherwise.

The CPE is always used to calculate the recipient address for a message.  Some
remote MTAs make a distinction based on localpart case, so we always send
messages to the case-preserved address.  Note that DNS is case insensitive so
it doesn't matter what the case is for the domain part of an email address,
although by default, we case-preserve that too.

The adaptors must support the readable interface for getting information about
memberships, and may optionally support the writeable interface.  If they do
not, then members cannot change their list attributes via Mailman's web or
email interfaces.  Updating membership information in that case is the
backend's responsibility.  Adaptors are allowed to support parts of the
writeable interface.

For any writeable method not supported, a NotImplemented exception should be
raised.

"""

class MemberAdaptor:
    #
    # The readable interface
    #
    def getMembers(self):
        """Get the LCE for all the members of the mailing list."""
        raise NotImplemented

    def getRegularMemberKeys(self):
        """Get the LCE for all regular delivery members (i.e. non-digest)."""
        raise NotImplemented

    def getDigestMemberKeys(self):
        """Get the LCE for all digest delivery members."""
        raise NotImplemented

    def isMember(self, member):
        """Return 1 if member KEY/LCE is a valid member, otherwise 0."""

    def getMemberKey(self, member):
        """Return the KEY for the member KEY/LCE.

        If member does not refer to a valid member, raise NotAMemberError.
        """
        raise NotImplemented

    def getMemberCPAddress(self, member):
        """Return the CPE for the member KEY/LCE.

        If member does not refer to a valid member, raise NotAMemberError.
        """
        raise NotImplemented

    def getMemberCPAddresses(self, members):
        """Return a sequence of CPEs for the given sequence of members.

        The returned sequence will be the same length as members.  If any of
        the KEY/LCEs in members does not refer to a valid member, that entry
        in the returned sequence will be None (i.e. NotAMemberError is never
        raised).
        """
        raise NotImplemented

    def authenticateMember(self, member, response):
        """Authenticate the member KEY/LCE with the given response.

        If the response authenticates the member, return a secret that is
        known only to the authenticated member.  This need not be the member's
        password, but it will be used to craft a session cookie, so it should
        be persistent for the life of the session.

        If the authentication failed return 0.  If member did not refer to a
        valid member, raise NotAMemberError.

        Normally, the response will be the password typed into a web form or
        given in an email command, but it needn't be.  It is up to the adaptor
        to compare the typed response to the user's authentication token.
        """
        raise NotImplemented

    def getMemberPassword(self, member):
        """Return the member's password.

        If the member KEY/LCE is not a member of the list, raise
        NotAMemberError.
        """

    def getMemberLanguage(self, member):
        """Return the preferred language for the member KEY/LCE.

        The language returned must be a key in mm_cfg.LC_DESCRIPTIONS and the
        mailing list must support that language.

        If member does not refer to a valid member, the list's default
        language is returned instead of raising a NotAMemberError error.
        """
        raise NotImplemented

    def getMemberOption(self, member, flag):
        """Return the boolean state of the member option for member KEY/LCE.

        Option flags are defined in Defaults.py.

        If member does not refer to a valid member, raise NotAMemberError.
        """
        raise NotImplemented

    def getMemberName(self, member):
        """Return the RealName of the member KEY/LCE.

        None is returned if the member has no registered RealName.
        NotAMemberError is raised if member does not refer to a valid member.
        """
        raise NotImplemented

    def getMemberTopics(self, member):
        """Return the list of topics this member is interested in.

        The return value is a list of strings which name the topics.
        """
        raise NotImplemented


    #
    # The writeable interface
    #
    def addNewMember(self, member, **kws):
        """Subscribes a new member to the mailing list.

        member is the case-preserved address to subscribe.  The LCE is
        calculated from this argument.  Return the new member KEY.

        This method also takes a keyword dictionary which can be used to set
        additional attributes on the member.  The actual set of supported
        keywords is adaptor specific, but should at least include:

        - digest == subscribing to digests instead of regular delivery
        - password == user's password
        - language == user's preferred language
        - realname == user's full Real Name

        Any values not passed to **kws is set to the adaptor-specific
        defaults.

        Raise AlreadyAMemberError it the member is already subscribed to the
        list.  Raises ValueError if **kws contains an invalid option.
        """
        raise NotImplemented

    def removeMember(self, memberkey):
        """Unsubscribes the member from the mailing list.

        Raise NotAMemberError if member is not subscribed to the list.
        """
        raise NotImplemented

    def changeMemberAddress(self, memberkey, newaddress, nodelete=0):
        """Change the address for the member KEY.

        memberkey will be a KEY, not an LCE.  newaddress should be the
        new case-preserved address for the member; the LCE will be calculated
        from newaddress.

        If memberkey does not refer to a valid member, raise NotAMemberError.
        No verification on the new address is done here (such assertions
        should be performed by the caller).

        If nodelete flag is true, then the old membership is not removed.
        """
        raise NotImplemented

    def setMemberPassword(self, member, password):
        """Set the password for member LCE/KEY.

        If member does not refer to a valid member, raise NotAMemberError.
        Also raise BadPasswordError if the password is illegal (e.g. too
        short or easily guessed via a dictionary attack).

        """
        raise NotImplemented

    def setMemberLanguage(self, member, language):
        """Set the language for the member LCE/KEY.

        If member does not refer to a valid member, raise NotAMemberError.
        Also raise BadLanguageError if the language is invalid (e.g. the list
        is not configured to support the given language).
        """
        raise NotImplemented

    def setMemberOption(self, member, flag, value):
        """Set the option for the given member to value.

        member is an LCE/KEY, flag is one of the option flags defined in
        Default.py, and value is a boolean.

        If member does not refer to a valid member, raise NotAMemberError.
        Also raise BadOptionError if the flag does not refer to a valid
        option.
        """
        raise NotImplemented

    def setMemberName(self, member, realname):
        """Set the member's RealName.

        member is an LCE/KEY and realname is an arbitrary string.
        NotAMemberError is raised if member does not refer to a valid member.
        """
        raise NotImplemented

    def setMemberTopics(self, member, topics):
        """Add list of topics to member's interest.

        member is an LCE/KEY and realname is an arbitrary string.
        NotAMemberError is raised if member does not refer to a valid member.
        topics must be a sequence of strings.
        """
        raise NotImplemented
