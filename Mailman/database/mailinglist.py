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

from storm.locals import *
from zope.interface import implements

from Mailman.Utils import fqdn_listname, makedirs, split_listname
from Mailman.configuration import config
from Mailman.database import roster
from Mailman.database.model import Model
from Mailman.database.types import Enum
from Mailman.interfaces import IMailingList, Personalization


SPACE = ' '
UNDERSCORE = '_'



class MailingList(Model):
    implements(IMailingList)

    id = Int(primary=True)

    # List identity
    list_name = Unicode()
    host_name = Unicode()
    # Attributes not directly modifiable via the web u/i
    created_at = DateTime()
    web_page_url = Unicode()
    admin_member_chunksize = Int()
    hold_and_cmd_autoresponses = Pickle()
    # Attributes which are directly modifiable via the web u/i.  The more
    # complicated attributes are currently stored as pickles, though that
    # will change as the schema and implementation is developed.
    next_request_id = Int()
    next_digest_number = Int()
    admin_responses = Pickle()
    postings_responses = Pickle()
    request_responses = Pickle()
    digest_last_sent_at = Float()
    one_last_digest = Pickle()
    volume = Int()
    last_post_time = DateTime()
    # Attributes which are directly modifiable via the web u/i.  The more
    # complicated attributes are currently stored as pickles, though that
    # will change as the schema and implementation is developed.
    accept_these_nonmembers = Pickle()
    acceptable_aliases = Pickle()
    admin_immed_notify = Bool()
    admin_notify_mchanges = Bool()
    administrivia = Bool()
    advertised = Bool()
    anonymous_list = Bool()
    archive = Bool()
    archive_private = Bool()
    archive_volume_frequency = Int()
    autorespond_admin = Bool()
    autorespond_postings = Bool()
    autorespond_requests = Int()
    autoresponse_admin_text = Unicode()
    autoresponse_graceperiod = TimeDelta()
    autoresponse_postings_text = Unicode()
    autoresponse_request_text = Unicode()
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
    collapse_alternatives = Bool()
    convert_html_to_plaintext = Bool()
    default_member_moderation = Bool()
    description = Unicode()
    digest_footer = Unicode()
    digest_header = Unicode()
    digest_is_default = Bool()
    digest_send_periodic = Bool()
    digest_size_threshold = Int()
    digest_volume_frequency = Int()
    digestable = Bool()
    discard_these_nonmembers = Pickle()
    emergency = Bool()
    encode_ascii_prefixes = Bool()
    filter_action = Int()
    filter_content = Bool()
    filter_filename_extensions = Pickle()
    filter_mime_types = Pickle()
    first_strip_reply_to = Bool()
    forward_auto_discards = Bool()
    gateway_to_mail = Bool()
    gateway_to_news = Bool()
    generic_nonmember_action = Int()
    goodbye_msg = Unicode()
    header_matches = Pickle()
    hold_these_nonmembers = Pickle()
    include_list_post_header = Bool()
    include_rfc2369_headers = Bool()
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
    pass_filename_extensions = Pickle()
    pass_mime_types = Pickle()
    personalize = Enum()
    post_id = Int()
    preferred_language = Unicode()
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
    def no_reply_address(self):
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
