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

"""In-memory implementations of Mailman interfaces, for testing purposes."""

import datetime
import urlparse

from Mailman import Utils
from Mailman import passwords
from Mailman.interfaces import *

from zope.interface import implements



class UserManager(object):
    implements(IUserManager)

    def __init__(self):
        self._users     = set()
        self._next_id   = 1

    @property
    def users(self):
        for user in self._users:
            yield user

    def create_user(self):
        user = User(self._next_id, self)
        self._next_id += 1
        self._users.add(user)
        return user

    def remove(self, user):
        self._users.discard(user)

    def get(self, address):
        # Yes, this is slow and icky, but it's only for testing purposes
        for user in self._users:
            if user.controls(address):
                return user
        return None



class User(object):
    implements(IUser)

    def __init__(self, user_id, user_mgr):
        self._user_id   = user_id
        self._user_mgr  = user_mgr
        self._addresses = set()
        self.real_name  = u''
        self.password   = passwords.NoPasswordScheme.make_secret('ignore')
        self.default_profile = None

    def __eq__(self, other):
        return (IUser.implementedBy(other) and
                self.user_id == other.user_id and
                self.user_manager is other.user_manager)

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def user_id(self):
        return self._user_id

    @property
    def user_manager(self):
        return self._user_mgr

    @property
    def addresses(self):
        for address in self._addresses:
            yield address

    def add_address(self, address):
        if self.controls(address):
            return
        user_address = Address(address, self)
        self._addresses.add(user_address)

    def remove_address(self, address):
        if not self.controls(address):
            return
        user_address = Address(address, self)
        self._addresses.discard(user_address)

    def controls(self, address):
        for user_address in self.addresses:
            if user_address == address:
                return True
        return False



class Address(object):
    implements(IAddress)

    def __init__(self, email_address, user, profile=None):
        self._address       = email_address
        self._user          = user
        self.profile        = profile or Profile()
        self.validated_on   = None

    def __eq__(self, other):
        return (IAddress.implementedBy(other) and
                self.address == other.address and
                self.user == other.user)

    @property
    def address(self):
        return self._address

    @property
    def user(self):
        return self._user



class RegularDelivery(object):
    implements(IRegularDelivery)


class PlainTextDigestDelivery(object):
    implements(IPlainTextDigestDelivery)


class MIMEDigestDelivery(object):
    implements(IMIMEDigestDeliver)



class DeliveryEnabled(object):
    implements(IDeliveryStatus)

    @property
    def enabled(self):
        return True


class DeliveryDisabled(object):
    implements(IDeliveryStatus)

    @property
    def enabled(self):
        return False


class DeliveryDisabledByUser(DeliveryDisabled):
    implements(IDeliveryDisabledByUser)


class DeliveryDisabledbyAdministrator(DeliveryDisabled):
    implements(IDeliveryDisabledByAdministrator)

    reason = u'Unknown'


class DeliveryDisabledByBounces(DeliveryDisabled):
    implements(IDeliveryDisabledByBounces)

    bounce_info = 'XXX'


class DeliveryTemporarilySuspended(object):
    implements(IDeliveryTemporarilySuspended)

    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date   = end_date

    @property
    def enabled(self):
        now = datetime.datetime.now()
        return not (self.start_date <= now < self.end_date)



class OkayToPost(object):
    implements(IPostingPermission)

    # XXX
    okay_to_post = True



class Profile(object):
    implements(IProfile)

    # System defaults
    acknowledge         = False
    hide                = True
    language            = 'en'
    list_copy           = True
    own_postings        = True
    delivery_mode       = RegularDelivery()
    delivery_status     = DeliveryEnabled()
    posting_permission  = OkayToPost()



class Roster(object):
    implements(IRoster)

    def __init__(self, name):
        self._name      = name
        self._members   = set()

    def __eq__(self, other):
        return (IRoster.implementedBy(other) and
                self.name == other.name)

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def name(self):
        return self._name

    def add(self, member):
        self._members.add(member)

    def remove(self, member):
        self._members.remove(member)

    @property
    def members(self):
        for member in self._members:
            yield member



class Member(object):
    implements(IMember)

    def __init__(self, address, roster, profile=None):
        self._address   = address
        self._roster    = roster
        self.profile    = profile or Profile()

    @property
    def address(self):
        return self._address

    @property
    def roster(self):
        return self._roster



class ListManager(object):
    implements(IListManager)

    def __init__(self):
        self._mlists = {}

    def add(self, mlist):
        self._mlists[mlist.fqdn_listname] = mlist

    def remove(self, mlist):
        del self._mlists[mlist.fqdn_listname]

    @property
    def mailing_lists(self):
        return self._mlists.itervalues()

    @property
    def names(self):
        return self._mlists.iterkeys()

    def get(self, fqdn_listname):
        return self._mlists.get(fqdn_listname)



class MailingList(object):
    implements(IMailingListIdentity,
               IMailingListAddresses,
               IMailingListURLs,
               IMailingListRosters,
               IMailingListStatistics,
               )

    def __init__(self, list_name, host_name, web_host):
        self._listname      = list_name
        self._hostname      = hostname
        self._webhost       = web_host
        self._fqdn_listname = Utils.fqdn_listname(list_name, host_name)
        # Rosters
        self._owners        = set(Roster(self.owner_address))
        self._moderators    = set(Roster(self._listname + '-moderators@' +
                                         self._hostname))
        self._members       = set(Roster(self.posting_address))
        # Statistics
        self._created_on    = datetime.datetime.now()
        self._last_posting  = None
        self._post_number   = 0
        self._last_digest   = None

    # IMailingListIdentity

    @property
    def list_name(self):
        return self._listname

    @property
    def host_name(self):
        return self._hostname

    @property
    def fqdn_listname(self):
        return self._fqdn_listname

    # IMailingListAddresses

    @property
    def posting_address(self):
        return self._fqdn_listname

    @property
    def noreply_address(self):
        return self._listname + '-noreply@' + self._hostname

    @property
    def owner_address(self):
        return self._listname + '-owner@' + self._hostname

    @property
    def request_address(self):
        return self._listname + '-request@' + self._hostname

    @property
    def bounces_address(self):
        return self._listname + '-bounces@' + self._hostname

    @property
    def confirm_address(self):
        return self._listname + '-confirm@' + self._hostname

    @property
    def join_address(self):
        return self._listname + '-join@' + self._hostname

    @property
    def leave_address(self):
        return self._listname + '-leave@' + self._hostname

    @property
    def subscribe_address(self):
        return self._listname + '-subscribe@' + self._hostname

    @property
    def unsubscribe_address(self):
        return self._listname + '-unsubscribe@' + self._hostname

    # IMailingListURLs

    protocol = 'http'

    @property
    def web_host(self):
        return self._webhost

    def script_url(self, target, context=None):
        if context is None:
            return urlparse.urlunsplit((self.protocol, self.web_host, target,
                                        # no extra query or fragment
                                        '', ''))
        return urlparse.urljoin(context.location, target)

    # IMailingListRosters

    @property
    def owner_rosters(self):
        return iter(self._owners)

    @property
    def moderator_rosters(self):
        return iter(self._moderators)

    @property
    def member_rosters(self):
        return iter(self._members)

    def add_owner_roster(self, roster):
        self._owners.add(roster)

    def add_moderator_roster(self, roster):
        self._moderators.add(roster)

    def add_member_roster(self, roster):
        self._members.add(roster)

    def remove_owner_roster(self, roster):
        self._owners.discard(roster)

    def remove_moderator_roster(self, roster):
        self._moderators.discard(roster)

    def remove_member_roster(self, roster):
        self._members.discard(roster)

    @property
    def owners(self):
        for roster in self._owners:
            for member in roster.members:
                yield member

    @property
    def moderators(self):
        for roster in self._moderators:
            for member in roster.members:
                yield member

    @property
    def administrators(self):
        for member in self.owners:
            yield member
        for member in self.moderators:
            yield member

    @property
    def members(self):
        for roster in self._members:
            for member in roster.members:
                yield member

    @property
    def regular_members(self):
        for member in self.members:
            if IRegularDelivery.implementedBy(member.profile.delivery_mode):
                yield member

    @property
    def digest_member(self):
        for member in self.members:
            if IDigestDelivery.implementedBy(member.profile.delivery_mode):
                yield member

    # Statistic

    @property
    def creation_date(self):
        return self._created_on

    @property
    def last_post_date(self):
        return self._last_posting

    @property
    def post_number(self):
        return self._post_number

    @property
    def last_digest_date(self):
        return self._last_digest



class MailingListRequest(object):
    implements(IMailingListRequest)

    location = ''



def initialize():
    from Mailman.configuration import config
    config.user_manager     = UserManager()
    config.list_manager     = ListManager()
    config.message_manager  = None
