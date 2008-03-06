# Copyright (C) 2007-2008 by the Free Software Foundation, Inc.
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

from storm.locals import *
from zope.interface import implements

from mailman.configuration import config
from mailman.constants import SystemDefaultPreferences
from mailman.database.address import Address
from mailman.database.member import Member
from mailman.interfaces import DeliveryMode, IRoster, MemberRole



class AbstractRoster(object):
    """An abstract IRoster class.

    This class takes the simple approach of implemented the 'users' and
    'addresses' properties in terms of the 'members' property.  This may not
    be the most efficient way, but it works.

    This requires that subclasses implement the 'members' property.
    """
    implements(IRoster)

    role = None

    def __init__(self, mlist):
        self._mlist = mlist

    @property
    def members(self):
        for member in config.db.store.find(
                Member,
                mailing_list=self._mlist.fqdn_listname,
                role=self.role):
            yield member

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

    def get_member(self, address):
        results = config.db.store.find(
            Member,
            Member.mailing_list == self._mlist.fqdn_listname,
            Member.role == self.role,
            Address.address == address,
            Member.address_id == Address.id)
        if results.count() == 0:
            return None
        elif results.count() == 1:
            return results[0]
        else:
            raise AssertionError('Too many matching member results: %s' %
                                 results.count())



class MemberRoster(AbstractRoster):
    """Return all the members of a list."""

    name = 'member'
    role = MemberRole.member



class OwnerRoster(AbstractRoster):
    """Return all the owners of a list."""

    name = 'owner'
    role = MemberRole.owner



class ModeratorRoster(AbstractRoster):
    """Return all the owners of a list."""

    name = 'moderator'
    role = MemberRole.moderator



class AdministratorRoster(AbstractRoster):
    """Return all the administrators of a list."""

    name = 'administrator'

    @property
    def members(self):
        # Administrators are defined as the union of the owners and the
        # moderators.
        members = config.db.store.find(
                Member,
                Member.mailing_list == self._mlist.fqdn_listname,
                Or(Member.role == MemberRole.owner,
                   Member.role == MemberRole.moderator))
        for member in members:
            yield member

    def get_member(self, address):
        results = config.db.store.find(
                Member,
                Member.mailing_list == self._mlist.fqdn_listname,
                Or(Member.role == MemberRole.moderator,
                   Member.role == MemberRole.owner),
                Address.address == address,
                Member.address_id == Address.id)
        if results.count() == 0:
            return None
        elif results.count() == 1:
            return results[0]
        else:
            raise AssertionError(
                'Too many matching member results: %s' % results)



class RegularMemberRoster(AbstractRoster):
    """Return all the regular delivery members of a list."""

    name = 'regular_members'

    @property
    def members(self):
        # Query for all the Members which have a role of MemberRole.member and
        # are subscribed to this mailing list.  Then return only those members
        # that have a regular delivery mode.
        for member in config.db.store.find(
                Member,
                mailing_list=self._mlist.fqdn_listname,
                role=MemberRole.member):
            if member.delivery_mode == DeliveryMode.regular:
                yield member



_digest_modes = (
    DeliveryMode.mime_digests,
    DeliveryMode.plaintext_digests,
    DeliveryMode.summary_digests,
    )



class DigestMemberRoster(AbstractRoster):
    """Return all the regular delivery members of a list."""

    name = 'digest_members'

    @property
    def members(self):
        # Query for all the Members which have a role of MemberRole.member and
        # are subscribed to this mailing list.  Then return only those members
        # that have one of the digest delivery modes.
        for member in config.db.store.find(
                Member,
                mailing_list=self._mlist.fqdn_listname,
                role=MemberRole.member):
            if member.delivery_mode in _digest_modes:
                yield member



class Subscribers(AbstractRoster):
    """Return all subscribed members regardless of their role."""

    name = 'subscribers'

    @property
    def members(self):
        for member in config.db.store.find(
                Member,
                mailing_list=self._mlist.fqdn_listname):
            yield member
