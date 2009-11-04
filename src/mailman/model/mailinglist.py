# Copyright (C) 2006-2009 by the Free Software Foundation, Inc.
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
from zope.interface import implements

from mailman.config import config
from mailman.database.model import Model
from mailman.database.types import Enum
from mailman.interfaces.domain import IDomainManager
from mailman.interfaces.mailinglist import (
    IAcceptableAlias, IAcceptableAliasSet, IMailingList, Personalization)
from mailman.interfaces.mime import FilterType
from mailman.model import roster
from mailman.model.digests import OneLastDigest
from mailman.model.mime import ContentFilter
from mailman.utilities.filesystem import makedirs
from mailman.utilities.string import expand


SPACE = ' '
UNDERSCORE = '_'



class MailingList(Model):
    implements(IMailingList)

    id = Int(primary=True)

    # List identity
    list_name = Unicode()
    host_name = Unicode()
    list_id = Unicode()
    include_list_post_header = Bool()
    include_rfc2369_headers = Bool()
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
    last_post_time = DateTime()
    # Implicit destination.
    acceptable_aliases_id = Int()
    acceptable_alias = Reference(acceptable_aliases_id, 'AcceptableAlias.id')
    # Attributes which are directly modifiable via the web u/i.  The more
    # complicated attributes are currently stored as pickles, though that
    # will change as the schema and implementation is developed.
    accept_these_nonmembers = Pickle()
    admin_immed_notify = Bool()
    admin_notify_mchanges = Bool()
    administrivia = Bool()
    advertised = Bool()
    anonymous_list = Bool()
    archive = Bool()
    archive_private = Bool()
    archive_volume_frequency = Int()
    # Automatic responses.
    autoresponse_grace_period = TimeDelta()
    autorespond_owner = Enum()
    autoresponse_owner_text = Unicode()
    autorespond_postings = Enum()
    autoresponse_postings_text = Unicode()
    autorespond_requests = Enum()
    autoresponse_request_text = Unicode()
    # Content filters.
    filter_content = Bool()
    collapse_alternatives = Bool()
    convert_html_to_plaintext = Bool()
    # Bounces and bans.
    ban_list = Pickle()
    bounce_info_stale_after = TimeDelta()
    bounce_matching_headers = Unicode()
    bounce_notify_owner_on_disable = Bool()
    bounce_notify_owner_on_removal = Bool()
    bounce_processing = Bool()
    bounce_score_threshold = Int()
    bounce_unrecognized_goes_to_list_owner = Bool()
    bounce_you_are_disabled_warnings = Int()
    bounce_you_are_disabled_warnings_interval = TimeDelta()
    default_member_moderation = Bool()
    description = Unicode()
    digest_footer = Unicode()
    digest_header = Unicode()
    digest_is_default = Bool()
    digest_send_periodic = Bool()
    digest_size_threshold = Float()
    digest_volume_frequency = Enum()
    digestable = Bool()
    discard_these_nonmembers = Pickle()
    emergency = Bool()
    encode_ascii_prefixes = Bool()
    first_strip_reply_to = Bool()
    forward_auto_discards = Bool()
    gateway_to_mail = Bool()
    gateway_to_news = Bool()
    generic_nonmember_action = Int()
    goodbye_msg = Unicode()
    header_matches = Pickle()
    hold_these_nonmembers = Pickle()
    info = Unicode()
    linked_newsgroup = Unicode()
    max_days_to_hold = Int()
    max_message_size = Int()
    max_num_recipients = Int()
    member_moderation_action = Enum()
    member_moderation_notice = Unicode()
    mime_is_default_digest = Bool()
    moderator_password = Unicode()
    msg_footer = Unicode()
    msg_header = Unicode()
    new_member_options = Int()
    news_moderation = Enum()
    news_prefix_subject_too = Bool()
    nntp_host = Unicode()
    nondigestable = Bool()
    nonmember_rejection_notice = Unicode()
    obscure_addresses = Bool()
    personalize = Enum()
    pipeline = Unicode()
    post_id = Int()
    _preferred_language = Unicode(name='preferred_language')
    private_roster = Bool()
    real_name = Unicode()
    reject_these_nonmembers = Pickle()
    reply_goes_to_list = Enum()
    reply_to_address = Unicode()
    require_explicit_destination = Bool()
    respond_to_post_requests = Bool()
    scrub_nondigest = Bool()
    send_goodbye_msg = Bool()
    send_reminders = Bool()
    send_welcome_msg = Bool()
    start_chain = Unicode()
    subject_prefix = Unicode()
    subscribe_auto_approval = Pickle()
    subscribe_policy = Int()
    topics = Pickle()
    topics_bodylines_limit = Int()
    topics_enabled = Bool()
    unsubscribe_policy = Int()
    welcome_msg = Unicode()

    def __init__(self, fqdn_listname):
        super(MailingList, self).__init__()
        listname, at, hostname = fqdn_listname.partition('@')
        assert hostname, 'Bad list name: {0}'.format(fqdn_listname)
        self.list_name = listname
        self.host_name = hostname
        # For the pending database
        self.next_request_id = 1
        self._restore()
        self.personalization = Personalization.none
        self.real_name = string.capwords(
            SPACE.join(listname.split(UNDERSCORE)))
        makedirs(self.data_path)

    # XXX FIXME
    def _restore(self):
        self.owners = roster.OwnerRoster(self)
        self.moderators = roster.ModeratorRoster(self)
        self.administrators = roster.AdministratorRoster(self)
        self.members = roster.MemberRoster(self)
        self.regular_members = roster.RegularMemberRoster(self)
        self.digest_members = roster.DigestMemberRoster(self)
        self.subscribers = roster.Subscribers(self)

    def __repr__(self):
        return '<mailing list "{0}" at {1:#x}>'.format(
            self.fqdn_listname, id(self))

    @property
    def fqdn_listname(self):
        """See `IMailingList`."""
        return '{0}@{1}'.format(self.list_name, self.host_name)

    @property
    def web_host(self):
        """See `IMailingList`."""
        return IDomainManager(config)[self.host_name]

    def script_url(self, target, context=None):
        """See `IMailingList`."""
        # Find the domain for this mailing list.
        domain = IDomainManager(config)[self.host_name]
        # XXX Handle the case for when context is not None; those would be
        # relative URLs.
        return urljoin(domain.base_url, target + '/' + self.fqdn_listname)

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
        return '{0}@{1}'.format(config.mailman.noreply_address, self.host_name)

    @property
    def owner_address(self):
        """See `IMailingList`."""
        return '{0}-owner@{1}'.format(self.list_name, self.host_name)

    @property
    def request_address(self):
        """See `IMailingList`."""
        return '{0}-request@{1}'.format(self.list_name, self.host_name)

    @property
    def bounces_address(self):
        """See `IMailingList`."""
        return '{0}-bounces@{1}'.format(self.list_name, self.host_name)

    @property
    def join_address(self):
        """See `IMailingList`."""
        return '{0}-join@{1}'.format(self.list_name, self.host_name)

    @property
    def leave_address(self):
        """See `IMailingList`."""
        return '{0}-leave@{1}'.format(self.list_name, self.host_name)

    @property
    def subscribe_address(self):
        """See `IMailingList`."""
        return '{0}-subscribe@{1}'.format(self.list_name, self.host_name)

    @property
    def unsubscribe_address(self):
        """See `IMailingList`."""
        return '{0}-unsubscribe@{1}'.format(self.list_name, self.host_name)

    def confirm_address(self, cookie):
        """See `IMailingList`."""
        local_part = expand(config.mta.verp_confirm_format, dict(
            address = '{0}-confirm'.format(self.list_name),
            cookie  = cookie))
        return '{0}@{1}'.format(local_part, self.host_name)

    @property
    def preferred_language(self):
        """See `IMailingList`."""
        return config.languages[self._preferred_language]

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
