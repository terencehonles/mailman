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

"""An implementation of an IRoster.

These are hard-coded rosters which know how to filter a set of members to find
the ones that fit a particular role.  These are used as the member, owner,
moderator, and administrator roster filters.
"""

from zope.interface import implements

from Mailman.constants import DeliveryMode, MemberRole
from Mailman.constants import SystemDefaultPreferences
from Mailman.database.model import Member
from Mailman.interfaces import IRoster



class AbstractRoster(object):
    """An abstract IRoster class.

    This class takes the simple approach of implemented the 'users' and
    'addresses' properties in terms of the 'members' property.  This may not
    be the most efficient way, but it works.

    This requires that subclasses implement the 'members' property.
    """
    implements(IRoster)

    def __init__(self, mlist):
        self._mlist = mlist

    @property
    def members(self):
        raise NotImplementedError

    @property
    def users(self):
        # Members are linked to addresses, which in turn are linked to users.
        # So while the 'members' attribute does most of the work, we have to
        # keep a set of unique users.  It's possible for the same user to be
        # subscribed to a mailing list multiple times with different
        # addresses.
        users = set(member.address.user for member in self.members)
        for user in users:
            yield user

    @property
    def addresses(self):
        # Every Member is linked to exactly one address so the 'members'
        # attribute does most of the work.
        for member in self.members:
            yield member.address



class MemberRoster(AbstractRoster):
    """Return all the members of a list."""

    name = 'member'

    @property
    def members(self):
        # Query for all the Members which have a role of MemberRole.member and
        # are subscribed to this mailing list.  XXX we have to use a private
        # data attribute of MailList for now.
        for member in Member.select_by(mailing_list=self._mlist.fqdn_listname,
                                       role=MemberRole.member):
            yield member



class OwnerRoster(AbstractRoster):
    """Return all the owners of a list."""

    name = 'owner'

    @property
    def members(self):
        # Query for all the Members which have a role of MemberRole.member and
        # are subscribed to this mailing list.  XXX we have to use a private
        # data attribute of MailList for now.
        for member in Member.select_by(mailing_list=self._mlist.fqdn_listname,
                                       role=MemberRole.owner):
            yield member



class ModeratorRoster(AbstractRoster):
    """Return all the owners of a list."""

    name = 'moderator'

    @property
    def members(self):
        # Query for all the Members which have a role of MemberRole.member and
        # are subscribed to this mailing list.  XXX we have to use a private
        # data attribute of MailList for now.
        for member in Member.select_by(mailing_list=self._mlist.fqdn_listname,
                                       role=MemberRole.moderator):
            yield member



class AdministratorRoster(AbstractRoster):
    """Return all the administrators of a list."""

    name = 'administrator'

    @property
    def members(self):
        # Administrators are defined as the union of the owners and the
        # moderators.  Until I figure out a more efficient way of doing this,
        # this will have to do.
        owners = Member.select_by(mailing_list=self._mlist.fqdn_listname,
                                  role=MemberRole.owner)
        moderators = Member.select_by(mailing_list=self._mlist.fqdn_listname,
                                      role=MemberRole.moderator)
        members = set(owners)
        members.update(set(moderators))
        for member in members:
            yield member



def _delivery_mode(member):
    if member.preferences.delivery_mode is not None:
        return member.preferences.delivery_mode
    if member.address.preferences.delivery_mode is not None:
        return member.address.preferences.delivery_mode
    if (member.address.user and
        member.address.user.preferences.delivery_mode is not None):
        return member.address.user.preferences.delivery_mode
    return SystemDefaultPreferences.delivery_mode


class RegularMemberRoster(AbstractRoster):
    """Return all the regular delivery members of a list."""

    name = 'regular_members'

    @property
    def members(self):
        # Query for all the Members which have a role of MemberRole.member and
        # are subscribed to this mailing list.  Then return only those members
        # that have a regular delivery mode.
        for member in Member.select_by(mailing_list=self._mlist.fqdn_listname,
                                       role=MemberRole.member):
            if _delivery_mode(member) == DeliveryMode.regular:
                yield member



_digest_modes = (
    DeliveryMode.mime_digests,
    DeliveryMode.plaintext_digests,
    DeliveryMode.summary_digests,
    )



class DigestMemberRoster(AbstractRoster):
    """Return all the regular delivery members of a list."""

    name = 'regular_members'

    @property
    def members(self):
        # Query for all the Members which have a role of MemberRole.member and
        # are subscribed to this mailing list.  Then return only those members
        # that have one of the digest delivery modes.
        for member in Member.select_by(mailing_list=self._mlist.fqdn_listname,
                                       role=MemberRole.member):
            if _delivery_mode(member) in _digest_modes:
                yield member
