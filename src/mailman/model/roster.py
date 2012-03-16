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

"""An implementation of an IRoster.

These are hard-coded rosters which know how to filter a set of members to find
the ones that fit a particular role.  These are used as the member, owner,
moderator, and administrator roster filters.
"""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'AdministratorRoster',
    'DigestMemberRoster',
    'MemberRoster',
    'Memberships',
    'ModeratorRoster',
    'OwnerRoster',
    'RegularMemberRoster',
    'Subscribers',
    ]


from storm.expr import And, Or
from zope.interface import implements

from mailman.config import config
from mailman.interfaces.member import DeliveryMode, MemberRole
from mailman.interfaces.roster import IRoster
from mailman.model.address import Address
from mailman.model.member import Member



class AbstractRoster:
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

    def _query(self):
        return config.db.store.find(
            Member,
            mailing_list=self._mlist.fqdn_listname,
            role=self.role)

    @property
    def members(self):
        """See `IRoster`."""
        for member in self._query():
            yield member

    @property
    def member_count(self):
        """See `IRoster`."""
        return self._query().count()

    @property
    def users(self):
        """See `IRoster`."""
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
        """See `IRoster`."""
        # Every Member is linked to exactly one address so the 'members'
        # attribute does most of the work.
        for member in self.members:
            yield member.address

    def get_member(self, address):
        """See `IRoster`."""
        results = config.db.store.find(
            Member,
            Member.mailing_list == self._mlist.fqdn_listname,
            Member.role == self.role,
            Address.email == address,
            Member.address_id == Address.id)
        if results.count() == 0:
            return None
        elif results.count() == 1:
            return results[0]
        else:
            raise AssertionError(
                'Too many matching member results: {0}'.format(
                    results.count()))



class MemberRoster(AbstractRoster):
    """Return all the members of a list."""

    name = 'member'
    role = MemberRole.member



class NonmemberRoster(AbstractRoster):
    """Return all the nonmembers of a list."""

    name = 'nonmember'
    role = MemberRole.nonmember



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

    def _query(self):
        return config.db.store.find(
            Member,
            Member.mailing_list == self._mlist.fqdn_listname,
            Or(Member.role == MemberRole.owner,
               Member.role == MemberRole.moderator))

    def get_member(self, address):
        """See `IRoster`."""
        results = config.db.store.find(
                Member,
                Member.mailing_list == self._mlist.fqdn_listname,
                Or(Member.role == MemberRole.moderator,
                   Member.role == MemberRole.owner),
                Address.email == address,
                Member.address_id == Address.id)
        if results.count() == 0:
            return None
        elif results.count() == 1:
            return results[0]
        else:
            raise AssertionError(
                'Too many matching member results: {0}'.format(results))



class DeliveryMemberRoster(AbstractRoster):
    """Return all the members having a particular kind of delivery."""

    @property
    def member_count(self):
        """See `IRoster`."""
        # XXX 2012-03-15 BAW: It would be nice to make this more efficient.
        # The problem is that you'd have to change the loop in _get_members()
        # checking the delivery mode to a query parameter.
        return len(tuple(self.members))

    def _get_members(self, *delivery_modes):
        """The set of members for a mailing list, filter by delivery mode.

        :param delivery_modes: The modes to filter on.
        :type delivery_modes: sequence of `DeliveryMode`.
        :return: A generator of members.
        :rtype: generator
        """
        results = config.db.store.find(
            Member,
            And(Member.mailing_list == self._mlist.fqdn_listname,
                Member.role == MemberRole.member))
        for member in results:
            if member.delivery_mode in delivery_modes:
                yield member


class RegularMemberRoster(DeliveryMemberRoster):
    """Return all the regular delivery members of a list."""

    name = 'regular_members'

    @property
    def members(self):
        """See `IRoster`."""
        for member in self._get_members(DeliveryMode.regular):
            yield member



class DigestMemberRoster(DeliveryMemberRoster):
    """Return all the regular delivery members of a list."""

    name = 'digest_members'

    @property
    def members(self):
        """See `IRoster`."""
        for member in self._get_members(DeliveryMode.plaintext_digests,
                                        DeliveryMode.mime_digests,
                                        DeliveryMode.summary_digests):
            yield member



class Subscribers(AbstractRoster):
    """Return all subscribed members regardless of their role."""

    name = 'subscribers'

    def _query(self):
        return config.db.store.find(
            Member,
            mailing_list=self._mlist.fqdn_listname)



class Memberships:
    """A roster of a single user's memberships."""

    implements(IRoster)

    name = 'memberships'

    def __init__(self, user):
        self._user = user

    def _query(self):
        results = config.db.store.find(
            Member,
            Or(Member.user_id == self._user.id,
               And(Address.user_id == self._user.id,
                   Member.address_id == Address.id)))
        return results.config(distinct=True)

    @property
    def member_count(self):
        """See `IRoster`."""
        return self._query().count()

    @property
    def members(self):
        """See `IRoster`."""
        for member in self._query():
            yield member

    @property
    def users(self):
        """See `IRoster`."""
        yield self._user

    @property
    def addresses(self):
        """See `IRoster`."""
        for address in self._user.addresses:
            yield address

    def get_member(self, address):
        """See `IRoster`."""
        results = config.db.store.find(
            Member,
            Member.address_id == Address.id,
            Address.user_id == self._user.id)
        if results.count() == 0:
            return None
        elif results.count() == 1:
            return results[0]
        else:
            raise AssertionError(
                'Too many matching member results: {0}'.format(
                    results.count()))
