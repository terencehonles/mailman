# Copyright (C) 2006-2007 by the Free Software Foundation, Inc.
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

import os
import string

from elixir import *
from zope.interface import implements

from Mailman.Utils import fqdn_listname, makedirs, split_listname
from Mailman.configuration import config
from Mailman.interfaces import IMailingList, Personalization
from Mailman.database.types import EnumType, TimeDeltaType

SPACE = ' '
UNDERSCORE = '_'



class MailingList(Entity):
    implements(IMailingList)

    # List identity
    list_name = Field(Unicode)
    host_name = Field(Unicode)
    # Attributes not directly modifiable via the web u/i
    created_at = Field(DateTime)
    web_page_url = Field(Unicode)
    admin_member_chunksize = Field(Integer)
    hold_and_cmd_autoresponses = Field(PickleType)
    # Attributes which are directly modifiable via the web u/i.  The more
    # complicated attributes are currently stored as pickles, though that
    # will change as the schema and implementation is developed.
    next_request_id = Field(Integer)
    next_digest_number = Field(Integer)
    admin_responses = Field(PickleType)
    postings_responses = Field(PickleType)
    request_responses = Field(PickleType)
    digest_last_sent_at = Field(Float)
    one_last_digest = Field(PickleType)
    volume = Field(Integer)
    last_post_time = Field(DateTime)
    # Attributes which are directly modifiable via the web u/i.  The more
    # complicated attributes are currently stored as pickles, though that
    # will change as the schema and implementation is developed.
    accept_these_nonmembers = Field(PickleType)
    acceptable_aliases = Field(PickleType)
    admin_immed_notify = Field(Boolean)
    admin_notify_mchanges = Field(Boolean)
    administrivia = Field(Boolean)
    advertised = Field(Boolean)
    anonymous_list = Field(Boolean)
    archive = Field(Boolean)
    archive_private = Field(Boolean)
    archive_volume_frequency = Field(Integer)
    autorespond_admin = Field(Boolean)
    autorespond_postings = Field(Boolean)
    autorespond_requests = Field(Integer)
    autoresponse_admin_text = Field(Unicode)
    autoresponse_graceperiod = Field(TimeDeltaType)
    autoresponse_postings_text = Field(Unicode)
    autoresponse_request_text = Field(Unicode)
    ban_list = Field(PickleType)
    bounce_info_stale_after = Field(TimeDeltaType)
    bounce_matching_headers = Field(Unicode)
    bounce_notify_owner_on_disable = Field(Boolean)
    bounce_notify_owner_on_removal = Field(Boolean)
    bounce_processing = Field(Boolean)
    bounce_score_threshold = Field(Integer)
    bounce_unrecognized_goes_to_list_owner = Field(Boolean)
    bounce_you_are_disabled_warnings = Field(Integer)
    bounce_you_are_disabled_warnings_interval = Field(TimeDeltaType)
    collapse_alternatives = Field(Boolean)
    convert_html_to_plaintext = Field(Boolean)
    default_member_moderation = Field(Boolean)
    description = Field(Unicode)
    digest_footer = Field(Unicode)
    digest_header = Field(Unicode)
    digest_is_default = Field(Boolean)
    digest_send_periodic = Field(Boolean)
    digest_size_threshold = Field(Integer)
    digest_volume_frequency = Field(Integer)
    digestable = Field(Boolean)
    discard_these_nonmembers = Field(PickleType)
    emergency = Field(Boolean)
    encode_ascii_prefixes = Field(Boolean)
    filter_action = Field(Integer)
    filter_content = Field(Boolean)
    filter_filename_extensions = Field(PickleType)
    filter_mime_types = Field(PickleType)
    first_strip_reply_to = Field(Boolean)
    forward_auto_discards = Field(Boolean)
    gateway_to_mail = Field(Boolean)
    gateway_to_news = Field(Boolean)
    generic_nonmember_action = Field(Integer)
    goodbye_msg = Field(Unicode)
    header_filter_rules = Field(PickleType)
    hold_these_nonmembers = Field(PickleType)
    include_list_post_header = Field(Boolean)
    include_rfc2369_headers = Field(Boolean)
    info = Field(Unicode)
    linked_newsgroup = Field(Unicode)
    max_days_to_hold = Field(Integer)
    max_message_size = Field(Integer)
    max_num_recipients = Field(Integer)
    member_moderation_action = Field(Boolean)
    member_moderation_notice = Field(Unicode)
    mime_is_default_digest = Field(Boolean)
    moderator_password = Field(Unicode)
    msg_footer = Field(Unicode)
    msg_header = Field(Unicode)
    new_member_options = Field(Integer)
    news_moderation = Field(EnumType)
    news_prefix_subject_too = Field(Boolean)
    nntp_host = Field(Unicode)
    nondigestable = Field(Boolean)
    nonmember_rejection_notice = Field(Unicode)
    obscure_addresses = Field(Boolean)
    pass_filename_extensions = Field(PickleType)
    pass_mime_types = Field(PickleType)
    personalize = Field(EnumType)
    post_id = Field(Integer)
    preferred_language = Field(Unicode)
    private_roster = Field(Boolean)
    real_name = Field(Unicode)
    reject_these_nonmembers = Field(PickleType)
    reply_goes_to_list = Field(EnumType)
    reply_to_address = Field(Unicode)
    require_explicit_destination = Field(Boolean)
    respond_to_post_requests = Field(Boolean)
    scrub_nondigest = Field(Boolean)
    send_goodbye_msg = Field(Boolean)
    send_reminders = Field(Boolean)
    send_welcome_msg = Field(Boolean)
    subject_prefix = Field(Unicode)
    subscribe_auto_approval = Field(PickleType)
    subscribe_policy = Field(Integer)
    topics = Field(PickleType)
    topics_bodylines_limit = Field(Integer)
    topics_enabled = Field(Boolean)
    unsubscribe_policy = Field(Integer)
    welcome_msg = Field(Unicode)
    # Relationships
##     has_and_belongs_to_many(
##         'available_languages',
##         of_kind='Mailman.database.model.languages.Language')

    def __init__(self, fqdn_listname):
        super(MailingList, self).__init__()
        listname, hostname = split_listname(fqdn_listname)
        self.list_name = listname
        self.host_name = hostname
        # For the pending database
        self.next_request_id = 1
        self._restore()
        # Max autoresponses per day.  A mapping between addresses and a
        # 2-tuple of the date of the last autoresponse and the number of
        # autoresponses sent on that date.
        self.hold_and_cmd_autoresponses = {}
        self.full_path = os.path.join(config.LIST_DATA_DIR, fqdn_listname)
        self.personalization = Personalization.none
        self.real_name = string.capwords(
            SPACE.join(listname.split(UNDERSCORE)))
        makedirs(self.full_path)

    # XXX FIXME
    def _restore(self):
        # Avoid circular imports.
        from Mailman.database.model import roster
        self.owners = roster.OwnerRoster(self)
        self.moderators = roster.ModeratorRoster(self)
        self.administrators = roster.AdministratorRoster(self)
        self.members = roster.MemberRoster(self)
        self.regular_members = roster.RegularMemberRoster(self)
        self.digest_members = roster.DigestMemberRoster(self)
        self.subscribers = roster.Subscribers(self)

    @property
    def fqdn_listname(self):
        """See IMailingListIdentity."""
        return fqdn_listname(self.list_name, self.host_name)

    @property
    def web_host(self):
        """See IMailingListWeb."""
        return config.domains[self.host_name]

    def script_url(self, target, context=None):
        """See IMailingListWeb."""
        # XXX Handle the case for when context is not None; those would be
        # relative URLs.
        return self.web_page_url + target + '/' + self.fqdn_listname

    # IMailingListAddresses

    @property
    def posting_address(self):
        return self.fqdn_listname

    @property
    def noreply_address(self):
        return '%s@%s' % (config.NO_REPLY_ADDRESS, self.host_name)

    @property
    def owner_address(self):
        return '%s-owner@%s' % (self.list_name, self.host_name)

    @property
    def request_address(self):
        return '%s-request@%s' % (self.list_name, self.host_name)

    @property
    def bounces_address(self):
        return '%s-bounces@%s' % (self.list_name, self.host_name)

    @property
    def join_address(self):
        return '%s-join@%s' % (self.list_name, self.host_name)

    @property
    def leave_address(self):
        return '%s-leave@%s' % (self.list_name, self.host_name)

    @property
    def subscribe_address(self):
        return '%s-subscribe@%s' % (self.list_name, self.host_name)

    @property
    def unsubscribe_address(self):
        return '%s-unsubscribe@%s' % (self.list_name, self.host_name)

    def confirm_address(self, cookie):
        template = string.Template(config.VERP_CONFIRM_FORMAT)
        local_part = template.safe_substitute(
            address = '%s-confirm' % self.list_name,
            cookie  = cookie)
        return '%s@%s' % (local_part, self.host_name)

    def __repr__(self):
        return '<mailing list "%s" at %#x>' % (self.fqdn_listname, id(self))
