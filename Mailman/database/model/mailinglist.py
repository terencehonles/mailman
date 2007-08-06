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

from elixir import *
from zope.interface import implements

from Mailman.Utils import fqdn_listname, split_listname
from Mailman.configuration import config
from Mailman.interfaces import *
from Mailman.database.types import EnumType, TimeDeltaType



class MailingList(Entity):
    implements(
        IMailingList,
        IMailingListAddresses,
        IMailingListIdentity,
        IMailingListRosters,
        IMailingListWeb,
        )

    # List identity
    has_field('list_name',                                  Unicode),
    has_field('host_name',                                  Unicode),
    # Attributes not directly modifiable via the web u/i
    has_field('created_at',                                 DateTime),
    has_field('web_page_url',                               Unicode),
    has_field('admin_member_chunksize',                     Integer),
    has_field('hold_and_cmd_autoresponses',                 PickleType),
    # Attributes which are directly modifiable via the web u/i.  The more
    # complicated attributes are currently stored as pickles, though that
    # will change as the schema and implementation is developed.
    has_field('next_request_id',                            Integer),
    has_field('next_digest_number',                         Integer),
    has_field('admin_responses',                            PickleType),
    has_field('postings_responses',                         PickleType),
    has_field('request_responses',                          PickleType),
    has_field('digest_last_sent_at',                        Float),
    has_field('one_last_digest',                            PickleType),
    has_field('volume',                                     Integer),
    has_field('last_post_time',                             DateTime),
    # Attributes which are directly modifiable via the web u/i.  The more
    # complicated attributes are currently stored as pickles, though that
    # will change as the schema and implementation is developed.
    has_field('accept_these_nonmembers',                    PickleType),
    has_field('acceptable_aliases',                         PickleType),
    has_field('admin_immed_notify',                         Boolean),
    has_field('admin_notify_mchanges',                      Boolean),
    has_field('administrivia',                              Boolean),
    has_field('advertised',                                 Boolean),
    has_field('anonymous_list',                             Boolean),
    has_field('archive',                                    Boolean),
    has_field('archive_private',                            Boolean),
    has_field('archive_volume_frequency',                   Integer),
    has_field('autorespond_admin',                          Boolean),
    has_field('autorespond_postings',                       Boolean),
    has_field('autorespond_requests',                       Integer),
    has_field('autoresponse_admin_text',                    Unicode),
    has_field('autoresponse_graceperiod',                   TimeDeltaType),
    has_field('autoresponse_postings_text',                 Unicode),
    has_field('autoresponse_request_text',                  Unicode),
    has_field('ban_list',                                   PickleType),
    has_field('bounce_info_stale_after',                    TimeDeltaType),
    has_field('bounce_matching_headers',                    Unicode),
    has_field('bounce_notify_owner_on_disable',             Boolean),
    has_field('bounce_notify_owner_on_removal',             Boolean),
    has_field('bounce_processing',                          Boolean),
    has_field('bounce_score_threshold',                     Integer),
    has_field('bounce_unrecognized_goes_to_list_owner',     Boolean),
    has_field('bounce_you_are_disabled_warnings',           Integer),
    has_field('bounce_you_are_disabled_warnings_interval',  TimeDeltaType),
    has_field('collapse_alternatives',                      Boolean),
    has_field('convert_html_to_plaintext',                  Boolean),
    has_field('default_member_moderation',                  Boolean),
    has_field('description',                                Unicode),
    has_field('digest_footer',                              Unicode),
    has_field('digest_header',                              Unicode),
    has_field('digest_is_default',                          Boolean),
    has_field('digest_send_periodic',                       Boolean),
    has_field('digest_size_threshold',                      Integer),
    has_field('digest_volume_frequency',                    Integer),
    has_field('digestable',                                 Boolean),
    has_field('discard_these_nonmembers',                   PickleType),
    has_field('emergency',                                  Boolean),
    has_field('encode_ascii_prefixes',                      Boolean),
    has_field('filter_action',                              Integer),
    has_field('filter_content',                             Boolean),
    has_field('filter_filename_extensions',                 PickleType),
    has_field('filter_mime_types',                          PickleType),
    has_field('first_strip_reply_to',                       Boolean),
    has_field('forward_auto_discards',                      Boolean),
    has_field('gateway_to_mail',                            Boolean),
    has_field('gateway_to_news',                            Boolean),
    has_field('generic_nonmember_action',                   Integer),
    has_field('goodbye_msg',                                Unicode),
    has_field('header_filter_rules',                        PickleType),
    has_field('hold_these_nonmembers',                      PickleType),
    has_field('include_list_post_header',                   Boolean),
    has_field('include_rfc2369_headers',                    Boolean),
    has_field('info',                                       Unicode),
    has_field('linked_newsgroup',                           Unicode),
    has_field('max_days_to_hold',                           Integer),
    has_field('max_message_size',                           Integer),
    has_field('max_num_recipients',                         Integer),
    has_field('member_moderation_action',                   Boolean),
    has_field('member_moderation_notice',                   Unicode),
    has_field('mime_is_default_digest',                     Boolean),
    has_field('mod_password',                               Unicode),
    has_field('msg_footer',                                 Unicode),
    has_field('msg_header',                                 Unicode),
    has_field('new_member_options',                         Integer),
    has_field('news_moderation',                            Boolean),
    has_field('news_prefix_subject_too',                    Boolean),
    has_field('nntp_host',                                  Unicode),
    has_field('nondigestable',                              Boolean),
    has_field('nonmember_rejection_notice',                 Unicode),
    has_field('obscure_addresses',                          Boolean),
    has_field('pass_filename_extensions',                   PickleType),
    has_field('pass_mime_types',                            PickleType),
    has_field('password',                                   Unicode),
    has_field('personalize',                                Integer),
    has_field('post_id',                                    Integer),
    has_field('preferred_language',                         Unicode),
    has_field('private_roster',                             Boolean),
    has_field('real_name',                                  Unicode),
    has_field('reject_these_nonmembers',                    PickleType),
    has_field('reply_goes_to_list',                         EnumType),
    has_field('reply_to_address',                           Unicode),
    has_field('require_explicit_destination',               Boolean),
    has_field('respond_to_post_requests',                   Boolean),
    has_field('scrub_nondigest',                            Boolean),
    has_field('send_goodbye_msg',                           Boolean),
    has_field('send_reminders',                             Boolean),
    has_field('send_welcome_msg',                           Boolean),
    has_field('subject_prefix',                             Unicode),
    has_field('subscribe_auto_approval',                    PickleType),
    has_field('subscribe_policy',                           Integer),
    has_field('topics',                                     PickleType),
    has_field('topics_bodylines_limit',                     Integer),
    has_field('topics_enabled',                             Boolean),
    has_field('unsubscribe_policy',                         Integer),
    has_field('welcome_msg',                                Unicode),
    # Relationships
##     has_and_belongs_to_many(
##         'available_languages',
##         of_kind='Mailman.database.model.languages.Language')
    # Options
    using_options(shortnames=True)

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
