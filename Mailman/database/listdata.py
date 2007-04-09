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

"""SQLAlchemy based list data storage."""

from sqlalchemy import *



def make_table(metadata, tables):
    table = Table(
        'Listdata', metadata,
        # Attributes not directly modifiable via the web u/i
        Column('list_id',                   Integer, primary_key=True),
        Column('list_name',                 Unicode),
        Column('web_page_url',              Unicode),
        Column('admin_member_chunksize',    Integer),
        Column('next_request_id',           Integer),
        Column('next_digest_number',        Integer),
        Column('admin_responses',           PickleType),
        Column('postings_responses',        PickleType),
        Column('request_responses',         PickleType),
        Column('digest_last_sent_at',       Float),
        Column('one_last_digest',           PickleType),
        Column('volume',                    Integer),
        Column('last_post_time',            Float),
        # OldStyleMemberships attributes, temporarily stored as pickles.
        Column('bounce_info',           PickleType),
        Column('delivery_status',       PickleType),
        Column('digest_members',        PickleType),
        Column('language',              PickleType),
        Column('members',               PickleType),
        Column('passwords',             PickleType),
        Column('topics_userinterest',   PickleType),
        Column('user_options',          PickleType),
        Column('usernames',             PickleType),
        # Attributes which are directly modifiable via the web u/i.  The more
        # complicated attributes are currently stored as pickles, though that
        # will change as the schema and implementation is developed.
        Column('accept_these_nonmembers',                       PickleType),
        Column('acceptable_aliases',                            PickleType),
        Column('admin_immed_notify',                            Boolean),
        Column('admin_notify_mchanges',                         Boolean),
        Column('administrivia',                                 Boolean),
        Column('advertised',                                    Boolean),
        Column('anonymous_list',                                Boolean),
        Column('archive',                                       Boolean),
        Column('archive_private',                               Boolean),
        Column('archive_volume_frequency',                      Integer),
        Column('autorespond_admin',                             Boolean),
        Column('autorespond_postings',                          Boolean),
        Column('autorespond_requests',                          Integer),
        Column('autoresponse_admin_text',                       Unicode),
        Column('autoresponse_graceperiod',                      Integer),
        Column('autoresponse_postings_text',                    Unicode),
        Column('autoresponse_request_text',                     Unicode),
        Column('ban_list',                                      PickleType),
        Column('bounce_info_stale_after',                       Integer),
        Column('bounce_matching_headers',                       Unicode),
        Column('bounce_notify_owner_on_disable',                Boolean),
        Column('bounce_notify_owner_on_removal',                Boolean),
        Column('bounce_processing',                             Boolean),
        Column('bounce_score_threshold',                        Integer),
        Column('bounce_unrecognized_goes_to_list_owner',        Boolean),
        Column('bounce_you_are_disabled_warnings',              Integer),
        Column('bounce_you_are_disabled_warnings_interval',     Integer),
        Column('collapse_alternatives',                         Boolean),
        Column('convert_html_to_plaintext',                     Boolean),
        Column('default_member_moderation',                     Boolean),
        Column('description',                                   Unicode),
        Column('digest_footer',                                 Unicode),
        Column('digest_header',                                 Unicode),
        Column('digest_is_default',                             Boolean),
        Column('digest_send_periodic',                          Boolean),
        Column('digest_size_threshhold',                        Integer),
        Column('digest_volume_frequency',                       Integer),
        Column('digestable',                                    Boolean),
        Column('discard_these_nonmembers',                      PickleType),
        Column('emergency',                                     Boolean),
        Column('encode_ascii_prefixes',                         Boolean),
        Column('filter_action',                                 Integer),
        Column('filter_content',                                Boolean),
        Column('filter_filename_extensions',                    PickleType),
        Column('filter_mime_types',                             PickleType),
        Column('first_strip_reply_to',                          Boolean),
        Column('forward_auto_discards',                         Boolean),
        Column('gateway_to_mail',                               Boolean),
        Column('gateway_to_news',                               Boolean),
        Column('generic_nonmember_action',                      Integer),
        Column('goodbye_msg',                                   Unicode),
        Column('header_filter_rules',                           PickleType),
        Column('hold_these_nonmembers',                         PickleType),
        Column('host_name',                                     Unicode),
        Column('include_list_post_header',                      Boolean),
        Column('include_rfc2369_headers',                       Boolean),
        Column('info',                                          Unicode),
        Column('linked_newsgroup',                              Unicode),
        Column('max_days_to_hold',                              Integer),
        Column('max_message_size',                              Integer),
        Column('max_num_recipients',                            Integer),
        Column('member_moderation_action',                      Boolean),
        Column('member_moderation_notice',                      Unicode),
        Column('mime_is_default_digest',                        Boolean),
        Column('mod_password',                                  Unicode),
        Column('moderator',                                     PickleType),
        Column('msg_footer',                                    Unicode),
        Column('msg_header',                                    Unicode),
        Column('new_member_options',                            Integer),
        Column('news_moderation',                               Boolean),
        Column('news_prefix_subject_too',                       Boolean),
        Column('nntp_host',                                     Unicode),
        Column('nondigestable',                                 Boolean),
        Column('nonmember_rejection_notice',                    Unicode),
        Column('obscure_addresses',                             Boolean),
        Column('owner',                                         PickleType),
        Column('pass_filename_extensions',                      PickleType),
        Column('pass_mime_types',                               PickleType),
        Column('password',                                      Unicode),
        Column('personalize',                                   Integer),
        Column('post_id',                                       Integer),
        Column('preferred_language',                            Unicode),
        Column('private_roster',                                Boolean),
        Column('real_name',                                     Unicode),
        Column('reject_these_nonmembers',                       PickleType),
        Column('reply_goes_to_list',                            Boolean),
        Column('reply_to_address',                              Unicode),
        Column('require_explicit_destination',                  Boolean),
        Column('respond_to_post_requests',                      Boolean),
        Column('scrub_nondigest',                               Boolean),
        Column('send_goodbye_msg',                              Boolean),
        Column('send_reminders',                                Boolean),
        Column('send_welcome_msg',                              Boolean),
        Column('subject_prefix',                                Unicode),
        Column('subscribe_auto_approval',                       PickleType),
        Column('subscribe_policy',                              Integer),
        Column('topics',                                        PickleType),
        Column('topics_bodylines_limit',                        Integer),
        Column('topics_enabled',                                Boolean),
        Column('umbrella_list',                                 Boolean),
        Column('umbrella_member_suffix',                        Unicode),
        Column('unsubscribe_policy',                            Integer),
        Column('welcome_msg',                                   Unicode),
        )
    # Avoid circular imports
    from Mailman.MailList import MailList
    from Mailman.database.languages import Language
    # We need to ensure MailList.InitTempVars() is called whenever a MailList
    # instance is created from a row.  Use a mapper extension for this.
    props = dict(available_languages=
                 relation(Language,
                          secondary=tables.available_languages,
                          lazy=False))
    mapper(MailList, table,
           extension=MailListMapperExtension(),
           properties=props)
    tables.bind(table)



class MailListMapperExtension(MapperExtension):
    def populate_instance(self, mapper, context, row, mlist, ikey, isnew):
        # Michael Bayer on the sqlalchemy mailing list:
        #
        # "isnew" is used to indicate that we are going to populate the
        # instance with data from the database, *and* that this particular row
        # is the first row in the result which has indicated the presence of
        # this entity (i.e. the primary key points to it).  this implies that
        # populate_instance() can be called *multiple times* for the instance,
        # if multiple successive rows all contain its particular primary key.
        if isnew:
            # Get the list name and host name -- which are required by
            # InitTempVars() from the row data.
            list_name = row['listdata_list_name']
            host_name = row['listdata_host_name']
            fqdn_name = '%s@%s' % (list_name, host_name)
            mlist.InitTempVars(fqdn_name)
        # In all cases, let SA proceed as normal
        return EXT_PASS
