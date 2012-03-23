# Copyright (C) 2006-2012 by the Free Software Foundation, Inc.
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

"""Model for mailing lists."""

from __future__ import absolute_import, unicode_literals

__metaclass__ = type
__all__ = [
    'MailingList',
    ]


import os
import string

from storm.locals import (
    And, Bool, DateTime, Float, Int, Pickle, Reference, Store, TimeDelta,
    Unicode)
from urlparse import urljoin
from zope.component import getUtility
from zope.interface import implements

from mailman.config import config
from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.interfaces.action import Action, FilterAction
from mailman.interfaces.address import IAddress
from mailman.interfaces.autorespond import ResponseAction
from mailman.interfaces.bounce import UnrecognizedBounceDisposition
from mailman.interfaces.digests import DigestFrequency
from mailman.interfaces.domain import IDomainManager
from mailman.interfaces.languages import ILanguageManager
from mailman.interfaces.mailinglist import (
    IAcceptableAlias, IAcceptableAliasSet, IMailingList, Personalization,
    ReplyToMunging)
from mailman.interfaces.member import (
    AlreadySubscribedError, MemberRole, MissingPreferredAddressError)
from mailman.interfaces.mime import FilterType
from mailman.interfaces.nntp import NewsModeration
from mailman.interfaces.user import IUser
from mailman.model import roster
from mailman.model.digests import OneLastDigest
from mailman.model.member import Member
from mailman.model.mime import ContentFilter
from mailman.model.preferences import Preferences
from mailman.utilities.filesystem import makedirs
from mailman.utilities.string import expand


SPACE = ' '
UNDERSCORE = '_'



class MailingList(Model):
    implements(IMailingList)

    id = Int(primary=True)

    # XXX denotes attributes that should be part of the public interface but
    # are currently missing.

    # List identity
    list_name = Unicode()
    mail_host = Unicode()
    include_list_post_header = Bool()
    include_rfc2369_headers = Bool()
    advertised = Bool()
    anonymous_list = Bool()
    # Attributes not directly modifiable via the web u/i
    created_at = DateTime()
    admin_member_chunksize = Int()
    # Attributes which are directly modifiable via the web u/i.  The more
    # complicated attributes are currently stored as pickles, though that
    # will change as the schema and implementation is developed.
    next_request_id = Int()
    next_digest_number = Int()
    digest_last_sent_at = DateTime()
    volume = Int()
    last_post_at = DateTime()
    # Implicit destination.
    acceptable_aliases_id = Int()
    acceptable_alias = Reference(acceptable_aliases_id, 'AcceptableAlias.id')
    # Attributes which are directly modifiable via the web u/i.  The more
    # complicated attributes are currently stored as pickles, though that
    # will change as the schema and implementation is developed.
    accept_these_nonmembers = Pickle() # XXX
    admin_immed_notify = Bool()
    admin_notify_mchanges = Bool()
    administrivia = Bool()
    archive = Bool() # XXX
    archive_private = Bool() # XXX
    archive_volume_frequency = Int() # XXX
    # Automatic responses.
    autoresponse_grace_period = TimeDelta()
    autorespond_owner = Enum(ResponseAction)
    autoresponse_owner_text = Unicode()
    autorespond_postings = Enum(ResponseAction)
    autoresponse_postings_text = Unicode()
    autorespond_requests = Enum(ResponseAction)
    autoresponse_request_text = Unicode()
    # Content filters.
    filter_action = Enum(FilterAction)
    filter_content = Bool()
    collapse_alternatives = Bool()
    convert_html_to_plaintext = Bool()
    # Bounces.
    bounce_info_stale_after = TimeDelta() # XXX
    bounce_matching_headers = Unicode() # XXX
    bounce_notify_owner_on_disable = Bool() # XXX
    bounce_notify_owner_on_removal = Bool() # XXX
    bounce_score_threshold = Int() # XXX
    bounce_you_are_disabled_warnings = Int() # XXX
    bounce_you_are_disabled_warnings_interval = TimeDelta() # XXX
    forward_unrecognized_bounces_to = Enum(UnrecognizedBounceDisposition)
    process_bounces = Bool()
    # Miscellaneous
    default_member_action = Enum(Action)
    default_nonmember_action = Enum(Action)
    description = Unicode()
    digest_footer_uri = Unicode()
    digest_header_uri = Unicode()
    digest_is_default = Bool()
    digest_send_periodic = Bool()
    digest_size_threshold = Float()
    digest_volume_frequency = Enum(DigestFrequency)
    digestable = Bool()
    discard_these_nonmembers = Pickle()
    emergency = Bool()
    encode_ascii_prefixes = Bool()
    first_strip_reply_to = Bool()
    footer_uri = Unicode()
    forward_auto_discards = Bool()
    gateway_to_mail = Bool()
    gateway_to_news = Bool()
    generic_nonmember_action = Int()
    goodbye_message_uri = Unicode()
    header_matches = Pickle()
    header_uri = Unicode()
    hold_these_nonmembers = Pickle()
    info = Unicode()
    linked_newsgroup = Unicode()
    max_days_to_hold = Int()
    max_message_size = Int()
    max_num_recipients = Int()
    member_moderation_notice = Unicode()
    mime_is_default_digest = Bool()
    moderator_password = Unicode()
    new_member_options = Int()
    news_moderation = Enum(NewsModeration)
    news_prefix_subject_too = Bool()
    nntp_host = Unicode()
    nondigestable = Bool()
    nonmember_rejection_notice = Unicode()
    obscure_addresses = Bool()
    owner_chain = Unicode()
    owner_pipeline = Unicode()
    personalize = Enum(Personalization)
    post_id = Int()
    posting_chain = Unicode()
    posting_pipeline = Unicode()
    _preferred_language = Unicode(name='preferred_language')
    private_roster = Bool()
    display_name = Unicode()
    reject_these_nonmembers = Pickle()
    reply_goes_to_list = Enum(ReplyToMunging)
    reply_to_address = Unicode()
    require_explicit_destination = Bool()
    respond_to_post_requests = Bool()
    scrub_nondigest = Bool()
    send_goodbye_message = Bool()
    send_reminders = Bool()
    send_welcome_message = Bool()
    subject_prefix = Unicode()
    subscribe_auto_approval = Pickle()
    subscribe_policy = Int()
    topics = Pickle()
    topics_bodylines_limit = Int()
    topics_enabled = Bool()
    unsubscribe_policy = Int()
    welcome_message_uri = Unicode()

    def __init__(self, fqdn_listname):
        super(MailingList, self).__init__()
        listname, at, hostname = fqdn_listname.partition('@')
        assert hostname, 'Bad list name: {0}'.format(fqdn_listname)
        self.list_name = listname
        self.mail_host = hostname
        # For the pending database
        self.next_request_id = 1
        # We need to set up the rosters.  Normally, this method will get
        # called when the MailingList object is loaded from the database, but
        # that's not the case when the constructor is called.  So, set up the
        # rosters explicitly.
        self.__storm_loaded__()
        self.personalize = Personalization.none
        self.display_name = string.capwords(
            SPACE.join(listname.split(UNDERSCORE)))
        makedirs(self.data_path)

    def __storm_loaded__(self):
        self.owners = roster.OwnerRoster(self)
        self.moderators = roster.ModeratorRoster(self)
        self.administrators = roster.AdministratorRoster(self)
        self.members = roster.MemberRoster(self)
        self.regular_members = roster.RegularMemberRoster(self)
        self.digest_members = roster.DigestMemberRoster(self)
        self.subscribers = roster.Subscribers(self)
        self.nonmembers = roster.NonmemberRoster(self)

    def __repr__(self):
        return '<mailing list "{0}" at {1:#x}>'.format(
            self.fqdn_listname, id(self))

    @property
    def fqdn_listname(self):
        """See `IMailingList`."""
        return '{0}@{1}'.format(self.list_name, self.mail_host)

    @property
    def domain(self):
        """See `IMailingList`."""
        return getUtility(IDomainManager)[self.mail_host]

    @property
    def scheme(self):
        """See `IMailingList`."""
        return self.domain.scheme

    @property
    def web_host(self):
        """See `IMailingList`."""
        return self.domain.url_host

    def script_url(self, target, context=None):
        """See `IMailingList`."""
        # XXX Handle the case for when context is not None; those would be
        # relative URLs.
        return urljoin(self.domain.base_url, target + '/' + self.fqdn_listname)

    @property
    def data_path(self):
        """See `IMailingList`."""
        return os.path.join(config.LIST_DATA_DIR, self.fqdn_listname)

    # IMailingListAddresses

    @property
    def posting_address(self):
        """See `IMailingList`."""
        return self.fqdn_listname

    @property
    def no_reply_address(self):
        """See `IMailingList`."""
        return '{0}@{1}'.format(config.mailman.noreply_address, self.mail_host)

    @property
    def owner_address(self):
        """See `IMailingList`."""
        return '{0}-owner@{1}'.format(self.list_name, self.mail_host)

    @property
    def request_address(self):
        """See `IMailingList`."""
        return '{0}-request@{1}'.format(self.list_name, self.mail_host)

    @property
    def bounces_address(self):
        """See `IMailingList`."""
        return '{0}-bounces@{1}'.format(self.list_name, self.mail_host)

    @property
    def join_address(self):
        """See `IMailingList`."""
        return '{0}-join@{1}'.format(self.list_name, self.mail_host)

    @property
    def leave_address(self):
        """See `IMailingList`."""
        return '{0}-leave@{1}'.format(self.list_name, self.mail_host)

    @property
    def subscribe_address(self):
        """See `IMailingList`."""
        return '{0}-subscribe@{1}'.format(self.list_name, self.mail_host)

    @property
    def unsubscribe_address(self):
        """See `IMailingList`."""
        return '{0}-unsubscribe@{1}'.format(self.list_name, self.mail_host)

    def confirm_address(self, cookie):
        """See `IMailingList`."""
        local_part = expand(config.mta.verp_confirm_format, dict(
            address = '{0}-confirm'.format(self.list_name),
            cookie  = cookie))
        return '{0}@{1}'.format(local_part, self.mail_host)

    @property
    def preferred_language(self):
        """See `IMailingList`."""
        return getUtility(ILanguageManager)[self._preferred_language]

    @preferred_language.setter
    def preferred_language(self, language):
        """See `IMailingList`."""
        # Accept both a language code and a `Language` instance.
        try:
            self._preferred_language = language.code
        except AttributeError:
            self._preferred_language = language

    def send_one_last_digest_to(self, address, delivery_mode):
        """See `IMailingList`."""
        digest = OneLastDigest(self, address, delivery_mode)
        Store.of(self).add(digest)

    @property
    def last_digest_recipients(self):
        """See `IMailingList`."""
        results = Store.of(self).find(
            OneLastDigest,
            OneLastDigest.mailing_list == self)
        recipients = [(digest.address, digest.delivery_mode)
                      for digest in results]
        results.remove()
        return recipients

    @property
    def filter_types(self):
        """See `IMailingList`."""
        results = Store.of(self).find(
            ContentFilter,
            And(ContentFilter.mailing_list == self,
                ContentFilter.filter_type == FilterType.filter_mime))
        for content_filter in results:
            yield content_filter.filter_pattern

    @filter_types.setter
    def filter_types(self, sequence):
        """See `IMailingList`."""
        # First, delete all existing MIME type filter patterns.
        store = Store.of(self)
        results = store.find(
            ContentFilter,
            And(ContentFilter.mailing_list == self,
                ContentFilter.filter_type == FilterType.filter_mime))
        results.remove()
        # Now add all the new filter types.
        for mime_type in sequence:
            content_filter = ContentFilter(
                self, mime_type, FilterType.filter_mime)
            store.add(content_filter)

    @property
    def pass_types(self):
        """See `IMailingList`."""
        results = Store.of(self).find(
            ContentFilter,
            And(ContentFilter.mailing_list == self,
                ContentFilter.filter_type == FilterType.pass_mime))
        for content_filter in results:
            yield content_filter.filter_pattern

    @pass_types.setter
    def pass_types(self, sequence):
        """See `IMailingList`."""
        # First, delete all existing MIME type pass patterns.
        store = Store.of(self)
        results = store.find(
            ContentFilter,
            And(ContentFilter.mailing_list == self,
                ContentFilter.filter_type == FilterType.pass_mime))
        results.remove()
        # Now add all the new filter types.
        for mime_type in sequence:
            content_filter = ContentFilter(
                self, mime_type, FilterType.pass_mime)
            store.add(content_filter)

    @property
    def filter_extensions(self):
        """See `IMailingList`."""
        results = Store.of(self).find(
            ContentFilter,
            And(ContentFilter.mailing_list == self,
                ContentFilter.filter_type == FilterType.filter_extension))
        for content_filter in results:
            yield content_filter.filter_pattern

    @filter_extensions.setter
    def filter_extensions(self, sequence):
        """See `IMailingList`."""
        # First, delete all existing file extensions filter patterns.
        store = Store.of(self)
        results = store.find(
            ContentFilter,
            And(ContentFilter.mailing_list == self,
                ContentFilter.filter_type == FilterType.filter_extension))
        results.remove()
        # Now add all the new filter types.
        for mime_type in sequence:
            content_filter = ContentFilter(
                self, mime_type, FilterType.filter_extension)
            store.add(content_filter)

    @property
    def pass_extensions(self):
        """See `IMailingList`."""
        results = Store.of(self).find(
            ContentFilter,
            And(ContentFilter.mailing_list == self,
                ContentFilter.filter_type == FilterType.pass_extension))
        for content_filter in results:
            yield content_filter.pass_pattern

    @pass_extensions.setter
    def pass_extensions(self, sequence):
        """See `IMailingList`."""
        # First, delete all existing file extensions pass patterns.
        store = Store.of(self)
        results = store.find(
            ContentFilter,
            And(ContentFilter.mailing_list == self,
                ContentFilter.filter_type == FilterType.pass_extension))
        results.remove()
        # Now add all the new filter types.
        for mime_type in sequence:
            content_filter = ContentFilter(
                self, mime_type, FilterType.pass_extension)
            store.add(content_filter)

    def get_roster(self, role):
        """See `IMailingList`."""
        if role is MemberRole.member:
            return self.members
        elif role is MemberRole.owner:
            return self.owners
        elif role is MemberRole.moderator:
            return self.moderators
        else:
            raise TypeError(
                'Undefined MemberRole: {0}'.format(role))

    def subscribe(self, subscriber, role=MemberRole.member):
        """See `IMailingList`."""
        store = Store.of(self)
        if IAddress.providedBy(subscriber):
            member = store.find(
                Member,
                Member.role == role,
                Member.mailing_list == self.fqdn_listname,
                Member._address == subscriber).one()
            if member:
                raise AlreadySubscribedError(
                    self.fqdn_listname, subscriber.email, role)
        elif IUser.providedBy(subscriber):
            if subscriber.preferred_address is None:
                raise MissingPreferredAddressError(subscriber)
            member = store.find(
                Member,
                Member.role == role,
                Member.mailing_list == self.fqdn_listname,
                Member._user == subscriber).one()
            if member:
                raise AlreadySubscribedError(
                    self.fqdn_listname, subscriber, role)
        else:
            raise ValueError('subscriber must be an address or user')
        member = Member(role=role,
                        mailing_list=self.fqdn_listname,
                        subscriber=subscriber)
        member.preferences = Preferences()
        store.add(member)
        return member



class AcceptableAlias(Model):
    implements(IAcceptableAlias)

    id = Int(primary=True)

    mailing_list_id = Int()
    mailing_list = Reference(mailing_list_id, MailingList.id)

    alias = Unicode()

    def __init__(self, mailing_list, alias):
        self.mailing_list = mailing_list
        self.alias = alias


class AcceptableAliasSet:
    implements(IAcceptableAliasSet)

    def __init__(self, mailing_list):
        self._mailing_list = mailing_list

    def clear(self):
        """See `IAcceptableAliasSet`."""
        Store.of(self._mailing_list).find(
            AcceptableAlias,
            AcceptableAlias.mailing_list == self._mailing_list).remove()

    def add(self, alias):
        if not (alias.startswith('^') or '@' in alias):
            raise ValueError(alias)
        alias = AcceptableAlias(self._mailing_list, alias.lower())
        Store.of(self._mailing_list).add(alias)

    def remove(self, alias):
        Store.of(self._mailing_list).find(
            AcceptableAlias,
            And(AcceptableAlias.mailing_list == self._mailing_list,
                AcceptableAlias.alias == alias.lower())).remove()

    @property
    def aliases(self):
        aliases = Store.of(self._mailing_list).find(
            AcceptableAlias,
            AcceptableAlias.mailing_list == self._mailing_list)
        for alias in aliases:
            yield alias.alias
